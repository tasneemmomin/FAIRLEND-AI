"""
Financial Stress Simulator service layer.

Responsibilities:
  - Load the active, versioned stress configuration (StressScenarioConfig).
  - Load application financials and separate VERIFIED intake values from
    estimated/computed assumption values (data integrity requirement).
  - Compute the baseline and orchestrate predefined/custom scenario suites,
    monthly projections and report export.
  - Guarantee scenario isolation: hypothetical values NEVER modify
    Application records. All writes here are limited to config rows,
    audit log entries and officer assessment notes.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.db.models import Application, AuditLog, StressScenarioConfig, User
from backend.core.security import decrypt_field
from backend.models.schemas import ApplicantIntakeRequest  # noqa: F401  (import guard)

from .calculations import (
    CALC_VERSION,
    calculate_emi,
    calculate_disposable_income,
    calculate_remaining_balance,
    calculate_foir,
    calculate_total_emi_burden,
    calculate_expense_burden_ratio,
)
from .scenarios import (
    generate_baseline_scenario,
    generate_income_reduction_scenarios,
    generate_expense_increase_scenarios,
    generate_additional_obligation_scenarios,
    generate_combined_scenarios,
    generate_custom_scenario,
)
from .stress_indicators import classify_stress, get_stress_metadata, classify_foir_risk
from .explanations import (
    generate_baseline_explanation,
    generate_stress_explanation,
)
from .projections import generate_monthly_projection
from .schemas import (
    DEFAULT_STRESS_CONFIG,
    deep_merge_config,
    CustomScenarioRequest,
    ProjectionRequest,
)


# ---------------------------------------------------------------------------
# Configuration management (admin; versioned, append-only)
# ---------------------------------------------------------------------------

def get_active_config(db: Session) -> dict:
    """Return the active stress config merged over documented defaults."""
    row = (
        db.query(StressScenarioConfig)
        .filter(StressScenarioConfig.is_active == True)  # noqa: E712
        .order_by(desc(StressScenarioConfig.config_version))
        .first()
    )
    payload = row.payload if row else {}
    merged = deep_merge_config(payload)
    merged["_config_row"] = {
        "config_version": row.config_version if row else 0,
        "updated_by": row.updated_by if row else "system_defaults",
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }
    # Strip non-serializable anything else
    return merged


def update_config(db: Session, payload: dict, updated_by: str, note: str | None = None) -> dict:
    """Append a new active configuration version; deactivate previous rows."""
    latest = (
        db.query(StressScenarioConfig)
        .order_by(desc(StressScenarioConfig.config_version))
        .first()
    )
    next_version = (latest.config_version if latest else 0) + 1

    db.query(StressScenarioConfig).filter(
        StressScenarioConfig.is_active == True  # noqa: E712
    ).update({"is_active": False})

    row = StressScenarioConfig(
        config_version=next_version,
        payload=payload,
        updated_by=updated_by or "system",
        is_active=True,
        note=note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "config_version": row.config_version,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat(),
        "payload": row.payload,
    }


def get_config_history(db: Session, limit: int = 20) -> list[dict]:
    rows = (
        db.query(StressScenarioConfig)
        .order_by(desc(StressScenarioConfig.config_version))
        .limit(max(1, limit))
        .all()
    )
    return [
        {
            "config_version": r.config_version,
            "updated_by": r.updated_by,
            "updated_at": r.updated_at.isoformat(),
            "is_active": r.is_active,
            "note": r.note,
            "payload": r.payload,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Application access control
# ---------------------------------------------------------------------------

def get_authorized_application(db: Session, application_id: str, user: User) -> Application:
    """Fetch an application enforcing role-based access and ownership."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise LookupError("Application not found")
    if user.role == "officer":
        return app
    if user.role == "applicant" and app.applicant_user_id == user.id:
        return app
    raise PermissionError("Access forbidden: you do not have permission to view this application.")


# ---------------------------------------------------------------------------
# Baseline financial inputs (verified vs assumption labelling)
# ---------------------------------------------------------------------------

def build_baseline_inputs(app: Application, config: dict) -> dict:
    """
    Build labelled financial inputs from the application record.
    Every value is tagged with its provenance:
      - verified_intake      : confirmed at application time
      - estimated_assumption : documented assumption when data is missing
      - computed_from_terms  : derived transparently from loan terms
    """
    rate = config.get("default_interest_rate_pct", 12.0)
    expense_ratio = config.get("estimated_expense_ratio", 0.40)

    monthly_income = float(app.monthly_income or 0.0)
    existing_emis = float(app.existing_emis or 0.0)
    requested_amount = float(app.requested_amount or 0.0)
    tenure = int(app.tenure_months or 0)

    provided_expenses = app.monthly_expenses if app.monthly_expenses is not None else None
    if provided_expenses is not None:
        monthly_expenses = float(provided_expenses)
        expenses_source = "verified_intake"
    else:
        monthly_expenses = round(monthly_income * expense_ratio, 2)
        expenses_source = "estimated_assumption"

    proposed_emi = calculate_emi(requested_amount, rate, tenure)

    return {
        "monthly_income": monthly_income,
        "existing_emis": existing_emis,
        "monthly_expenses": monthly_expenses,
        "requested_amount": requested_amount,
        "tenure_months": tenure,
        "proposed_emi": proposed_emi,
        "interest_rate_pct": rate,
        "data_sources": {
            "monthly_income": "verified_intake",
            "existing_emis": "verified_intake",
            "monthly_expenses": expenses_source,
            "requested_amount": "verified_intake",
            "tenure_months": "verified_intake",
            "proposed_emi": "computed_from_terms",
            "interest_rate_pct": "policy_configuration",
        },
        "insufficient_income_data": monthly_income <= 0,
    }


def compute_baseline(app: Application, config: dict) -> dict:
    inputs = build_baseline_inputs(app, config)
    ni = inputs["monthly_income"]
    insuff = inputs["insufficient_income_data"]

    disposable = calculate_disposable_income(ni, inputs["existing_emis"], inputs["monthly_expenses"])
    remaining = calculate_remaining_balance(
        ni, inputs["existing_emis"], inputs["monthly_expenses"], inputs["proposed_emi"]
    )
    foir = calculate_foir(inputs["existing_emis"], inputs["proposed_emi"], ni)
    total_emi = calculate_total_emi_burden(inputs["existing_emis"], inputs["proposed_emi"])

    thresholds = config.get("stress_thresholds")
    stress = classify_stress(remaining, ni, thresholds)
    meta = get_stress_metadata(stress)

    baseline_payload = {
        "net_income": ni,
        "monthly_expenses": inputs["monthly_expenses"],
        "existing_emis": inputs["existing_emis"],
        "proposed_emi": inputs["proposed_emi"],
        "remaining_balance": remaining,
        "foir": foir,
        "stress_indicator": stress.value,
    }

    key_factors = _derive_key_factors(inputs, remaining, foir, config)
    return {
        "inputs": inputs,
        "disposable_income": disposable,
        "remaining_balance": remaining,
        "total_emi_burden": total_emi,
        "expense_burden_ratio": calculate_expense_burden_ratio(inputs["monthly_expenses"], ni),
        "foir": foir,
        "foir_risk_band": classify_foir_risk(foir, config.get("foir_bands")),
        "stress_indicator": stress.value,
        "stress_label": meta["label"],
        "stress_color": meta["color"],
        "stress_description": meta["description"],
        "explanation": generate_baseline_explanation(baseline_payload),
        "overall_assessment": generate_stress_explanation(
            (stress.value if not insuff else "INSUFFICIENT_DATA"), key_factors
        ),
        "key_factors": key_factors,
        "calc_version": config.get("calc_version", CALC_VERSION),
        "insufficient_income_data": insuff,
    }


def _derive_key_factors(inputs: dict, remaining: float, foir: float, config: dict) -> list[str]:
    """Identify the financial assumptions currently causing concern."""
    factors: list[str] = []
    ni = inputs["monthly_income"]
    bands = config.get("foir_bands", {})

    if remaining < 0:
        factors.append(
            f"Monthly deficit of Rs.{abs(remaining):,.0f} after all obligations"
        )
    elif ni > 0 and remaining < config.get("stress_thresholds", {}).get("reduced_buffer_min_ratio", 0.10) * ni:
        factors.append(
            f"Post-loan surplus of Rs.{remaining:,.0f} is under 10% of monthly income"
        )
    if bands and foir > bands.get("moderate", 45.0):
        factors.append(f"FOIR of {foir:.1f}% exceeds the moderate policy band")
    if inputs["data_sources"]["monthly_expenses"] == "estimated_assumption":
        factors.append(
            "Living expenses are an estimated assumption (applicant has not provided verified expenses)"
        )
    if inputs["existing_emis"] > 0:
        factors.append(f"Existing EMI obligations of Rs.{inputs['existing_emis']:,.0f} already present")
    return factors


# ---------------------------------------------------------------------------
# Scenario orchestration
# ---------------------------------------------------------------------------

def run_full_simulation(db: Session, application: Application) -> dict:
    """Run the full predefined scenario suite (Scenarios A–E) for an application."""
    config = get_active_config(db)
    baseline = compute_baseline(application, config)
    inputs = baseline["inputs"]
    bl = {
        "net_income": inputs["monthly_income"],
        "monthly_expenses": inputs["monthly_expenses"],
        "existing_emis": inputs["existing_emis"],
        "proposed_emi": inputs["proposed_emi"],
        "remaining_balance": baseline["remaining_balance"],
        "foir": baseline["foir"],
        "stress_indicator": baseline["stress_indicator"],
    }

    scenario_a = generate_baseline_scenario(
        inputs["monthly_income"], inputs["existing_emis"], inputs["monthly_expenses"],
        inputs["proposed_emi"], bl, config,
    )
    scenario_b = generate_income_reduction_scenarios(
        inputs["monthly_income"], inputs["existing_emis"], inputs["monthly_expenses"],
        inputs["proposed_emi"], bl,
        steps=config.get("income_reduction_steps"), config=config,
    )
    scenario_c = generate_expense_increase_scenarios(
        inputs["monthly_income"], inputs["existing_emis"], inputs["monthly_expenses"],
        inputs["proposed_emi"], bl,
        steps=config.get("expense_increase_steps"), config=config,
    )
    scenario_d = generate_additional_obligation_scenarios(
        inputs["monthly_income"], inputs["existing_emis"], inputs["monthly_expenses"],
        inputs["proposed_emi"], bl,
        obligation_defs=config.get("additional_obligation_scenarios"), config=config,
    )
    scenario_e = generate_combined_scenarios(
        inputs["monthly_income"], inputs["existing_emis"], inputs["monthly_expenses"],
        inputs["proposed_emi"], bl,
        presets=config.get("combined_stress_presets"), config=config,
    )
    default_projection = generate_monthly_projection(
        inputs["monthly_income"], inputs["existing_emis"], inputs["monthly_expenses"],
        inputs["proposed_emi"], months=config.get("projection_months_default", 12),
        baseline=bl,
    )

    return {
        "application_id": application.id,
        "calc_version": config.get("calc_version", CALC_VERSION),
        "config_version": config.get("_config_row", {}).get("config_version", 0),
        "inputs": inputs,
        "scenario_a_current": scenario_a,
        "scenario_b_income_reduction": scenario_b,
        "scenario_c_expense_increase": scenario_c,
        "scenario_d_additional_obligations": scenario_d,
        "scenario_e_combined": scenario_e,
        "worst_case_summary": _worst_case_summary(bl, scenario_b, scenario_c, scenario_e),
        "default_projection": default_projection,
        "disclaimer": (
            "All scenario values are hypothetical assumptions. They do not modify the "
            "application record and do not predict actual future events or loan default."
        ),
    }


def _worst_case_summary(baseline: dict, scenario_b: list, scenario_c: list, scenario_e: list) -> dict:
    """Worst balance across generated scenarios with the scenario that caused it."""
    candidates = []
    for s in scenario_b + scenario_c + scenario_e:
        candidates.append((s["remaining_balance"], s["scenario_name"]))
    if not candidates:
        return {}
    worst_balance, worst_name = min(candidates, key=lambda t: t[0])
    return {
        "worst_scenario_name": worst_name,
        "worst_remaining_balance": worst_balance,
        "baseline_remaining_balance": baseline["remaining_balance"],
        "worst_relative_to_baseline": round(worst_balance - baseline["remaining_balance"], 2),
    }


def run_custom_application_scenario(application: Application, req: CustomScenarioRequest, config: dict) -> dict:
    """Run a single user-customized scenario after clamping to permitted ranges."""
    limits = config.get("simulation_limits", {})
    income_reduction = clamp(
        req.income_reduction_pct,
        limits.get("income_reduction_min_pct", 0.0),
        limits.get("income_reduction_max_pct", 50.0),
    )
    expense_increase = clamp(
        req.expense_increase_pct,
        limits.get("expense_increase_min_pct", 0.0),
        limits.get("expense_increase_max_pct", 150.0),
    )
    additional = clamp(req.additional_obligation, 0.0, limits.get("additional_obligation_max_inr", 200000.0))

    inputs = build_baseline_inputs(application, config)
    proposed_emi = inputs["proposed_emi"]
    custom_emi = req.proposed_emi
    if custom_emi is not None:
        custom_emi = clamp(custom_emi, 0.0, proposed_emi * limits.get("proposed_emi_max_multiplier", 10.0))

    bl = {
        "net_income": inputs["monthly_income"],
        "monthly_expenses": inputs["monthly_expenses"],
        "existing_emis": inputs["existing_emis"],
        "proposed_emi": proposed_emi,
        "remaining_balance": calculate_remaining_balance(
            inputs["monthly_income"], inputs["existing_emis"],
            inputs["monthly_expenses"], proposed_emi,
        ),
        "foir": calculate_foir(inputs["existing_emis"], proposed_emi, inputs["monthly_income"]),
        "stress_indicator": "",
    }
    return generate_custom_scenario(
        income_reduction_pct=income_reduction,
        expense_increase_pct=expense_increase,
        additional_obligation=additional,
        baseline_income=inputs["monthly_income"],
        existing_emis=inputs["existing_emis"],
        baseline_expenses=inputs["monthly_expenses"],
        proposed_emi=proposed_emi,
        custom_proposed_emi=custom_emi,
        baseline=bl,
        config=config,
    )


def run_application_projection(application: Application, req: ProjectionRequest, config: dict) -> dict:
    """Run the assumption-based monthly projection for an application."""
    inputs = build_baseline_inputs(application, config)
    months = min(req.months, config.get("projection_months_max", 24))
    proposed_emi = req.proposed_emi if req.proposed_emi is not None else inputs["proposed_emi"]
    limits = config.get("simulation_limits", {})
    if req.proposed_emi is not None:
        proposed_emi = clamp(
            proposed_emi, 0.0, inputs["proposed_emi"] * limits.get("proposed_emi_max_multiplier", 10.0)
        )
    return generate_monthly_projection(
        baseline_income=inputs["monthly_income"],
        existing_emis=inputs["existing_emis"],
        monthly_expenses=inputs["monthly_expenses"],
        proposed_emi=proposed_emi,
        monthly_income_change_pct=req.monthly_income_change_pct,
        expense_growth_pct=req.expense_growth_pct,
        additional_obligation=req.additional_obligation,
        months=months,
    )


# ---------------------------------------------------------------------------
# Report export (audit-logged)
# ---------------------------------------------------------------------------

def export_stress_report(db: Session, application: Application, user: User, config: dict | None = None) -> dict:
    """Build a full, self-contained stress analysis report and log the export."""
    config = config or get_active_config(db)
    simulation = run_full_simulation(db, application)
    applicant_name = decrypt_field(application.applicant_name_enc) or "Applicant"

    report = {
        "report_id": str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_for_role": user.role,
        "application_id": application.id,
        "applicant_name": applicant_name,
        "loan_terms": {
            "requested_amount": simulation["inputs"]["requested_amount"],
            "tenure_months": simulation["inputs"]["tenure_months"],
            "interest_rate_pct": simulation["inputs"]["interest_rate_pct"],
            "proposed_emi": simulation["inputs"]["proposed_emi"],
        },
        "data_sources": simulation["inputs"]["data_sources"],
        "calc_version": simulation["calc_version"],
        "config_version": simulation["config_version"],
        "baseline": simulation["scenario_a_current"],
        "income_reduction_scenarios": simulation["scenario_b_income_reduction"],
        "expense_increase_scenarios": simulation["scenario_c_expense_increase"],
        "additional_obligation_scenarios": simulation["scenario_d_additional_obligations"],
        "combined_scenarios": simulation["scenario_e_combined"],
        "worst_case_summary": simulation["worst_case_summary"],
        "monthly_projection": simulation["default_projection"],
        "overall_assessment": baseline_overall(simulation),
        "important_disclaimer": (
            "This report contains hypothetical scenario analysis only. Results are "
            "deterministic calculations under stated assumptions; they are not forecasts "
            "of future events and do not constitute loan approval advice."
        ),
    }

    db.add(AuditLog(
        user_role=user.role,
        user_id=user.id,
        action="stress_report_exported",
        resource_id=application.id,
        details={"report_id": report["report_id"], "calc_version": report["calc_version"]},
    ))
    db.commit()
    return report


def baseline_overall(simulation: dict) -> str:
    """Pull the baseline overall assessment text out of a full simulation."""
    current = simulation.get("scenario_a_current") or {}
    return current.get("explanation", "")


# ---------------------------------------------------------------------------
# Officer advisory assessment (stored as audit log; advisory only)
# ---------------------------------------------------------------------------

def record_officer_assessment(db: Session, application: Application, user: User, note: str) -> dict:
    entry = AuditLog(
        user_role="officer",
        user_id=user.id,
        action="stress_assessment_recorded",
        resource_id=application.id,
        details={"assessment_note": note},
    )
    db.add(entry)
    db.commit()
    return {
        "application_id": application.id,
        "recorded": True,
        "recorded_at": entry.timestamp.isoformat(),
        "advisory": True,
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def clamp(value: float, minimum: float, maximum: float) -> float:
    if value is None:
        return minimum
    return round(max(minimum, min(maximum, float(value))), 2)
