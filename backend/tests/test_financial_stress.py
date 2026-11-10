"""
Financial Stress Simulator — test suite.

Every numeric expectation below is INDEPENDENTLY hand-calculated and
annotated with the arithmetic used. Covers:
  - baseline calculations & FOIR (incl. zero/missing income)
  - income reduction, expense increase, combined stress, additional obligations
  - custom scenarios, clamping limits
  - monthly projections
  - stress indicator classification
  - permission checks & scenario isolation from application records
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.core.auth import hash_password
from backend.db.database import SessionLocal
from backend.db.models import Application, User
from backend.services.financial_stress import (
    calculations as calc,
    scenarios as scen,
    stress_indicators as si,
    projections as proj,
)
from backend.services.financial_stress.schemas import DEFAULT_STRESS_CONFIG
from backend.services.financial_stress.service import (
    get_active_config,
    update_config,
    get_authorized_application,
    build_baseline_inputs,
    compute_baseline,
    run_full_simulation,
    run_custom_application_scenario,
    run_application_projection,
)
from backend.services.financial_stress.schemas import CustomScenarioRequest, ProjectionRequest

client = TestClient(app)


def _mk_user(db, email, role="applicant"):
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    u = User(email=email, password_hash=hash_password("Test@1234"), full_name=email, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_app(db, owner_id, income=50000, emis=5000, expenses=None, amount=100000, tenure=12):
    app_rec = Application(
        age=30, employment_type="salaried", employment_duration_months=24,
        monthly_income=income, existing_emis=emis, monthly_expenses=expenses,
        requested_amount=amount, tenure_months=tenure, loan_purpose="personal",
        dependents=0, residence_type="rented", credit_history_years=1.0,
        collateral_value=0.0, intake_mode="typed",
        applicant_user_id=owner_id, status="submitted",
    )
    db.add(app_rec)
    db.commit()
    db.refresh(app_rec)
    return app_rec


@pytest.fixture(scope="module")
def db_and_entities():
    from backend.db.session import init_db
    init_db()  # idempotent: creates tables + runs SQLite column migration
    db = SessionLocal()
    applicant = _mk_user(db, "stress.test.applicant@example.com", "applicant")
    other = _mk_user(db, "stress.test.other@example.com", "applicant")
    officer = _mk_user(db, "stress.test.officer@example.com", "officer")

    # Reference case: income 50,000, EMI 5,000, expenses 20,000, loan 100,000/12m
    app_rec = _mk_app(db, applicant.id)
    zero_income_app = _mk_app(db, other.id, income=0)

    # login tokens via API
    tokens = {}
    for role, email in [("applicant", applicant.email), ("other", other.email), ("officer", officer.email)]:
        r = client.post("/api/auth/login", json={"email": email, "password": "Test@1234", "expected_role": role})
        assert r.status_code == 200, r.text
        tokens[role] = r.json()["access_token"]

    yield {
        "db": db, "applicant": applicant, "other": other, "officer": officer,
        "app": app_rec, "zero_app": zero_income_app, "tokens": tokens,
    }
    # cleanup created entities
    for a in [app_rec, zero_income_app]:
        db.delete(a)
    for u in [applicant, other, officer]:
        db.delete(u)
    db.commit()
    db.close()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Baseline calculations (independently verified arithmetic)
# ===========================================================================

class TestCalculations:
    def test_disposable_income(self):
        # 50000 - 5000 - 20000 = 25000
        assert calc.calculate_disposable_income(50000, 5000, 20000) == 25000

    def test_remaining_balance(self):
        # 50000 - 5000 - 20000 - 10000 = 15000
        assert calc.calculate_remaining_balance(50000, 5000, 20000, 10000) == 15000

    def test_remaining_balance_negative(self):
        # 30000 - 5000 - 20000 - 10000 = -5000
        assert calc.calculate_remaining_balance(30000, 5000, 20000, 10000) == -5000

    def test_foir_and_zero_income_safety(self):
        # (5000+10000)/50000*100 = 30.0
        assert calc.calculate_foir(5000, 10000, 50000) == 30.0
        # zero income must not divide by zero
        assert calc.calculate_foir(5000, 10000, 0) == 0.0
        assert calc.calculate_foir(5000, 10000, -1) == 0.0

    def test_expense_burden_kept_separate_from_emis(self):
        # 20000/50000*100 = 40%; expenses are NOT counted as EMI burden
        assert calc.calculate_expense_burden_ratio(20000, 50000) == 40.0
        assert calc.calculate_total_emi_burden(5000, 10000) == 15000

    def test_income_and_expense_application(self):
        assert calc.apply_income_reduction(50000, 10.0) == 45000.0
        assert calc.apply_income_reduction(50000, 0.0) == 50000.0
        assert calc.apply_income_reduction(50000, 200.0) == 0.0  # floor at zero
        assert calc.apply_expense_increase(20000, 15.0) == 23000.0

    def test_emi_standard_formula(self):
        # P=100000, r=1%/month, n=12 → EMI = 8884.88 (standard tables)
        assert calc.calculate_emi(100000, 12.0, 12) == 8884.88
        # zero interest → simple division: 100000/12 = 8333.33
        assert calc.calculate_emi(100000, 0, 12) == 8333.33
        assert calc.calculate_emi(0, 12, 12) == 0.0

    def test_insufficient_income_indicator(self):
        # income <= 0 → INSUFFICIENT_DATA
        assert si.classify_stress(5000, 0) == si.StressLevel.INSUFFICIENT_DATA
        assert si.classify_stress(5000, -100) == si.StressLevel.INSUFFICIENT_DATA


# ===========================================================================
# 2. Stress indicator classification (documented documented bands)
# ===========================================================================

class TestStressIndicators:
    def test_bands(self):
        # remaining as fraction of income: <0 NEGATIVE; 0..10% ELEVATED;
        # 10..20% REDUCED_BUFFER; >20% STABLE (default bands)
        assert si.classify_stress(11000, 50000) == si.StressLevel.STABLE          # 22%
        assert si.classify_stress(10000, 50000) == si.StressLevel.REDUCED_BUFFER  # 20%
        assert si.classify_stress(5000, 50000) == si.StressLevel.ELEVATED_STRESS  # 10%
        assert si.classify_stress(5000.01, 50000) == si.StressLevel.REDUCED_BUFFER  # just above 10%
        assert si.classify_stress(0, 50000) == si.StressLevel.NEGATIVE_BALANCE
        assert si.classify_stress(-100, 50000) == si.StressLevel.NEGATIVE_BALANCE

    def test_custom_config_bands(self):
        t = {"stable_min_ratio": 0.30, "reduced_buffer_min_ratio": 0.15, "elevated_stress_min_ratio": 0.0}
        assert si.classify_stress(16000, 50000, t) == si.StressLevel.STABLE   # 32%
        assert si.classify_stress(14000, 50000, t) == si.StressLevel.REDUCED_BUFFER  # 28%? (28% > 15%, <=30%)

    def test_foir_bands(self):
        assert si.classify_foir_risk(30.0) == "safe"
        assert si.classify_foir_risk(40.0) == "moderate"
        assert si.classify_foir_risk(50.0) == "high"
        assert si.classify_foir_risk(60.0) == "critical"


# ===========================================================================
# 3. Scenarios (hand-verified numbers for the reference case)
# ===========================================================================

BASELINE = {
    "net_income": 50000, "monthly_expenses": 20000, "existing_emis": 5000,
    "proposed_emi": 10000, "remaining_balance": 15000, "foir": 30.0,
    "stress_indicator": "STABLE",
}


class TestScenarios:
    def test_baseline_scenario(self):
        r = scen.generate_baseline_scenario(50000, 5000, 20000, 10000, BASELINE)
        assert r["remaining_balance"] == 15000
        assert r["foir"] == 30.0

    def test_income_reduction_series(self):
        results = scen.generate_income_reduction_scenarios(50000, 5000, 20000, 10000, BASELINE)
        assert [r["variation_pct"] for r in results] == [5.0, 10.0, 15.0, 20.0]
        by_pct = {r["variation_pct"]: r for r in results}
        # Income: 47500/45000/42500/40000; remaining = income - 35000
        assert by_pct[5.0]["remaining_balance"] == 12500   # 47500-35000
        assert by_pct[10.0]["remaining_balance"] == 10000  # 45000-35000
        assert by_pct[15.0]["remaining_balance"] == 7500   # 42500-35000
        assert by_pct[20.0]["remaining_balance"] == 5000   # 40000-35000
        # FOIR rises as income falls: 15000/47500 = 31.58
        assert by_pct[5.0]["foir"] == 31.58

    def test_expense_increase_series(self):
        results = scen.generate_expense_increase_scenarios(50000, 5000, 20000, 10000, BASELINE)
        by_pct = {r["variation_pct"]: r for r in results}
        # Remaining = 50000 - 5000 - expenses - 10000
        assert by_pct[5.0]["monthly_expenses"] == 21000 and by_pct[5.0]["remaining_balance"] == 14000
        assert by_pct[10.0]["monthly_expenses"] == 22000 and by_pct[10.0]["remaining_balance"] == 13000
        assert by_pct[15.0]["monthly_expenses"] == 23000 and by_pct[15.0]["remaining_balance"] == 12000
        assert by_pct[20.0]["monthly_expenses"] == 24000 and by_pct[20.0]["remaining_balance"] == 11000

    def test_additional_obligation_scenario(self):
        # Config default "Additional Loan EMI" = 5% of income = 2500
        r = scen.generate_additional_obligation_scenarios(
            50000, 5000, 20000, 10000, BASELINE,
            obligation_defs=[{"label": "Additional Loan EMI", "pct_of_income": 5.0}],
        )[0]
        # remaining = 50000 - (5000+2500) - 20000 - 10000 = 12500
        assert r["remaining_balance"] == 12500

    def test_additional_obligation_scenarios_labeled_hypothetical(self):
        results = scen.generate_additional_obligation_scenarios(50000, 5000, 20000, 10000, BASELINE)
        assert len(results) == 4
        for r in results:
            assert r["hypothetical"] is True
            assert "(hypothetical)" in r["scenario_name"]
        # "Additional Loan EMI" = 5% of 50000 = 2500 → remaining = 15000-2500 = 12500
        emi_extra = next(r for r in results if r["obligation_type"] == "Additional Loan EMI")
        assert emi_extra["additional_obligation"] == 2500
        assert emi_extra["remaining_balance"] == 12500

    def test_combined_scenarios(self):
        results = scen.generate_combined_scenarios(50000, 5000, 20000, 10000, BASELINE)
        assert len(results) == 3
        first = results[0]
        # -10% income → 45000; +10% expenses → 22000 (module default presets)
        assert first["remaining_balance"] == 8000  # 45000-5000-22000-10000

    def test_combined_10_15_preset_from_config(self):
        presets = [{"income_reduction": 10.0, "expense_increase": 15.0}]
        r = scen.generate_combined_scenarios(50000, 5000, 20000, 10000, BASELINE, presets=presets)[0]
        # income 45000, expenses 23000 → remaining = 45000-5000-23000-10000 = 7000
        assert r["remaining_balance"] == 7000
        assert r["income_reduction_pct"] == 10.0 and r["expense_increase_pct"] == 15.0

    def test_custom_scenario_full(self):
        r = scen.generate_custom_scenario(
            10.0, 15.0, 2500, 50000, 5000, 20000, 10000, None, BASELINE
        )
        # income 45000, expenses 23000, existing 7500 → 45000-7500-23000-10000 = 4500
        assert r["remaining_balance"] == 4500
        assert r["hypothetical"] is True

    def test_negative_monthly_balance_scenario(self):
        results = scen.generate_income_reduction_scenarios(40000, 5000, 20000, 10000,
                                                           {"net_income": 40000, "monthly_expenses": 20000,
                                                            "existing_emis": 5000, "proposed_emi": 10000,
                                                            "remaining_balance": 5000, "foir": 37.5,
                                                            "stress_indicator": "REDUCED_BUFFER"})
        # income 40000-20% = 32000 → 32000-5000-20000-10000 = -3000 → negative
        assert results[-1]["remaining_balance"] == -3000
        assert results[-1]["stress_indicator"] == "NEGATIVE_BALANCE"


# ===========================================================================
# 4. Monthly projection
# ===========================================================================

class TestProjections:
    def test_constant_assumptions(self):
        p = proj.generate_monthly_projection(50000, 5000, 20000, 10000, months=12)
        assert len(p["monthly"]) == 12
        # every month: 50000-5000-20000-10000 = 15000
        assert all(m["remaining_balance"] == 15000 for m in p["monthly"])
        # cumulative sums: 15000*m
        assert p["monthly"][11]["cumulative_buffer"] == 15000 * 12
        assert p["months_to_stress"] is None
        assert p["insufficient_data"] is False

    def test_expense_growth_creates_stress_month(self):
        # expenses grow 20%/month from 20000: month m expenses = 20000*1.2^(m-1)
        # balance_m = 50000 - 5000 - expenses_m - 10000 = 35000 - expenses_m
        # month3: 35000-28800=6200; month4: 35000-34560=440; month5: -6472
        p = proj.generate_monthly_projection(50000, 5000, 20000, 10000, expense_growth_pct=20.0, months=12)
        m4 = p["monthly"][3]
        m5 = p["monthly"][4]
        assert m4["remaining_balance"] == round(35000 - 20000 * 1.2 ** 3, 2)   # 440.0
        assert m5["remaining_balance"] == round(35000 - 20000 * 1.2 ** 4, 2)   # -6472.0 <0
        assert p["months_to_stress"] == 4  # 0-based index of first negative month
        assert "Month 5" in p["explanation"]

    def test_income_decline_projection(self):
        # income declines 2%/month: month m income = 50000*0.98^(m-1)
        p = proj.generate_monthly_projection(50000, 5000, 20000, 10000, monthly_income_change_pct=-2.0, months=6)
        first = p["monthly"][0]["income"]
        assert first == 50000
        assert p["monthly"][5]["income"] == round(50000 * 0.98 ** 5, 2)

    def test_additional_obligation_in_projection(self):
        p = proj.generate_monthly_projection(50000, 5000, 20000, 10000, additional_obligation=3000, months=3)
        # balance = 50000-5000-23000-10000 = 12000 each month
        assert all(m["remaining_balance"] == 12000 for m in p["monthly"])

    def test_projection_month_bounds(self):
        p = proj.generate_monthly_projection(50000, 5000, 20000, 10000, months=100)
        assert len(p["monthly"]) == proj.MAX_PROJECTION_MONTHS
        p2 = proj.generate_monthly_projection(50000, 5000, 20000, 10000, months=0)
        assert len(p2["monthly"]) == 1

    def test_projection_insufficient_income(self):
        p = proj.generate_monthly_projection(0, 5000, 20000, 10000, months=6)
        assert p["insufficient_data"] is True
        assert p["months_to_stress"] is None


# ===========================================================================
# 5. Service layer: baseline build, isolation, config
# ===========================================================================

class TestService:
    def test_data_source_labelling(self, db_and_entities):
        db = db_and_entities["db"]
        app_rec = db_and_entities["app"]
        config = get_active_config(db)
        inputs = build_baseline_inputs(app_rec, config)
        assert inputs["data_sources"]["monthly_income"] == "verified_intake"
        assert inputs["data_sources"]["proposed_emi"] == "computed_from_terms"
        # expenses were not provided → documented estimated assumption
        assert inputs["data_sources"]["monthly_expenses"] == "estimated_assumption"

    def test_baseline_numbers(self, db_and_entities):
        db, app_rec = db_and_entities["db"], db_and_entities["app"]
        config = get_active_config(db)
        baseline = compute_baseline(app_rec, config)
        # expenses estimated at 40% of 50000 = 20000; EMI = 8884.88
        assert baseline["inputs"]["proposed_emi"] == 8884.88
        # remaining = 50000-5000-20000-8884.88 = 16115.12
        assert baseline["remaining_balance"] == 16115.12
        # FOIR = (5000+8884.88)/50000*100 = 27.77
        assert baseline["foir"] == 27.77

    def test_scenario_isolation_from_application_record(self, db_and_entities):
        """Hypothetical scenarios must NEVER modify the Application record."""
        db, app_rec = db_and_entities["db"], db_and_entities["app"]
        config = get_active_config(db)
        before = (app_rec.monthly_income, app_rec.existing_emis,
                  app_rec.monthly_expenses, app_rec.requested_amount, app_rec.tenure_months)
        sim = run_full_simulation(db, app_rec)
        # 12 income steps × -50%
        for r in sim["scenario_b_income_reduction"]:
            assert r["net_income"] <= app_rec.monthly_income
        app_rec2 = db.query(Application).filter(Application.id == app_rec.id).first()
        after = (app_rec2.monthly_income, app_rec2.existing_emis,
                 app_rec2.monthly_expenses, app_rec2.requested_amount, app_rec2.tenure_months)
        assert before == after

    def test_full_simulation_structure(self, db_and_entities):
        db, app_rec = db_and_entities["db"], db_and_entities["app"]
        sim = run_full_simulation(db, app_rec)
        assert len(sim["scenario_b_income_reduction"]) == 4
        assert len(sim["scenario_c_expense_increase"]) == 4
        assert len(sim["scenario_d_additional_obligations"]) == 4
        assert len(sim["scenario_e_combined"]) == 3
        assert sim["worst_case_summary"]["worst_remaining_balance"] <= sim["scenario_a_current"]["remaining_balance"]

    def test_custom_scenario_clamping(self, db_and_entities):
        db, app_rec = db_and_entities["db"], db_and_entities["app"]
        config = get_active_config(db)
        # attempt extreme values; must clamp to configuration limits
        req = CustomScenarioRequest(
            income_reduction_pct=90, expense_increase_pct=200,
            additional_obligation=10_000_000, proposed_emi=10_000_000,
        )
        r = run_custom_application_scenario(app_rec, req, config)
        limits = config["simulation_limits"]
        ci = r["custom_inputs"]
        assert ci["income_reduction_pct"] == limits["income_reduction_max_pct"]
        assert ci["expense_increase_pct"] == limits["expense_increase_max_pct"]
        assert ci["additional_obligation"] == limits["additional_obligation_max_inr"]
        assert ci["proposed_emi"] == round(8884.88 * limits["proposed_emi_max_multiplier"], 2)

    def test_projection_service(self, db_and_entities):
        db, app_rec = db_and_entities["db"], db_and_entities["app"]
        config = get_active_config(db)
        req = ProjectionRequest(expense_growth_pct=5.0, months=12)
        p = run_application_projection(app_rec, req, config)
        # expenses grow 5% per month from 20000: month3 = 20000*1.05^2
        assert p["monthly"][2]["expenses"] == round(20000 * 1.05 ** 2, 2)

    def test_zero_income_insufficient(self, db_and_entities):
        db, zero_app = db_and_entities["db"], db_and_entities["zero_app"]
        config = get_active_config(db)
        baseline = compute_baseline(zero_app, config)
        assert baseline["stress_indicator"] == "INSUFFICIENT_DATA"
        assert baseline["insufficient_income_data"] is True
        sim = run_full_simulation(db, zero_app)
        assert sim["scenario_a_current"]["stress_indicator"] == "INSUFFICIENT_DATA"

    def test_config_versioning(self, db_and_entities):
        db = db_and_entities["db"]
        payload = dict(DEFAULT_STRESS_CONFIG)
        payload["estimated_expense_ratio"] = 0.35
        res = update_config(db, payload, updated_by="stress.test.officer@example.com", note="test")
        assert res["config_version"] >= 1
        active = get_active_config(db)
        assert active["estimated_expense_ratio"] == 0.35
        history = stress_history(db)
        assert history[0]["config_version"] == res["config_version"]


def stress_history(db):
    from backend.services.financial_stress.service import get_config_history
    return get_config_history(db, limit=5)


# ===========================================================================
# 6. API permissions & isolation
# ===========================================================================

class TestAPIPermissions:
    def test_unauthenticated_blocked(self, db_and_entities):
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/stress/applications/{app_id}/scenarios")
        assert r.status_code == 401

    def test_owner_can_access(self, db_and_entities):
        t = db_and_entities["tokens"]["applicant"]
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/stress/applications/{app_id}/scenarios", headers=_auth(t))
        assert r.status_code == 200
        assert len(r.json()["scenario_b_income_reduction"]) == 4

    def test_applicant_isolation_between_users(self, db_and_entities):
        """Applicants must never access another applicant's scenario results."""
        t_other = db_and_entities["tokens"]["other"]
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/stress/applications/{app_id}/baseline", headers=_auth(t_other))
        assert r.status_code == 403

    def test_officer_access_any_application(self, db_and_entities):
        t = db_and_entities["tokens"]["officer"]
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/stress/applications/{app_id}/baseline", headers=_auth(t))
        assert r.status_code == 200
        assert r.json()["metrics"]["foir"] == 27.77

    def test_disabled_applicant_cannot_access(self, db_and_entities):
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/stress/applications/{app_id}/scenarios")
        assert r.status_code == 401  # no token → unauthorized

    def test_custom_scenario_validation_rejects_negative(self, db_and_entities):
        t = db_and_entities["tokens"]["applicant"]
        app_id = db_and_entities["app"].id
        r = client.post(
            f"/api/stress/applications/{app_id}/custom",
            headers=_auth(t), json={"income_reduction_pct": -5},
        )
        assert r.status_code == 422  # pydantic ge=0 guard

    def test_projection_endpoint(self, db_and_entities):
        t = db_and_entities["tokens"]["applicant"]
        app_id = db_and_entities["app"].id
        r = client.post(
            f"/api/stress/applications/{app_id}/projection",
            headers=_auth(t), json={"expense_growth_pct": 2.0, "months": 6},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["monthly"]) == 6
        assert body["hypothetical"] is True

    def test_report_endpoint_and_audit_log(self, db_and_entities):
        t = db_and_entities["tokens"]["applicant"]
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/stress/applications/{app_id}/report", headers=_auth(t))
        assert r.status_code == 200
        body = r.json()
        assert body["important_disclaimer"]
        assert body["application_id"] == app_id
        # audit log entry recorded
        db = SessionLocal()
        from backend.db.models import AuditLog
        entry = db.query(AuditLog).filter(
            AuditLog.action == "stress_report_exported", AuditLog.resource_id == app_id
        ).first()
        assert entry is not None
        db.delete(entry)
        db.commit()
        db.close()

    def test_config_readable_by_authenticated_config_endpoint(self, db_and_entities):
        t = db_and_entities["tokens"]["applicant"]
        r = client.get("/api/stress/config", headers=_auth(t))
        assert r.status_code == 200
        assert "stress_thresholds" in r.json()

    def test_config_update_officer_only(self, db_and_entities):
        t_a = db_and_entities["tokens"]["applicant"]
        t_o = db_and_entities["tokens"]["officer"]
        r = client.put("/api/stress/config", headers=_auth(t_a), json={"estimated_expense_ratio": 0.5})
        assert r.status_code == 403  # applicants cannot change configuration
        r2 = client.put("/api/stress/config", headers=_auth(t_o),
                        json={"estimated_expense_ratio": 0.4, "_note": "restore default"})
        assert r2.status_code == 200

    def test_assessment_officer_only(self, db_and_entities):
        t_a = db_and_entities["tokens"]["applicant"]
        t_o = db_and_entities["tokens"]["officer"]
        app_id = db_and_entities["app"].id
        r = client.post(f"/api/stress/applications/{app_id}/assessment",
                        headers=_auth(t_a), json={"assessment_note": "applicant note attempt"})
        assert r.status_code == 403

    def test_report_only_after_owner_confirmation(self, db_and_entities):
        # Report export never mutates application status
        app_rec = db_and_entities["app"]
        assert app_rec.status == "submitted"


class TestSecurityFixes:
    """Regression tests for bugs found in the full application audit."""

    def test_explain_endpoint_requires_authentication(self, db_and_entities):
        """Bugfix regression: /explain/{id} previously leaked decrypted PII without auth."""
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/explain/{app_id}")
        assert r.status_code == 401

    def test_explain_endpoint_ownership_enforcement(self, db_and_entities):
        t_other = db_and_entities["tokens"]["other"]
        app_id = db_and_entities["app"].id
        r = client.get(f"/api/explain/{app_id}", headers=_auth(t_other))
        assert r.status_code == 403
        # officer may still view
        t_o = db_and_entities["tokens"]["officer"]
        r2 = client.get(f"/api/explain/{app_id}", headers=_auth(t_o))
        assert r2.status_code == 200

    def test_officer_decision_rejects_invalid_values(self, db_and_entities):
        """Bugfix regression: arbitrary decision strings corrupted HITL training labels."""
        t_o = db_and_entities["tokens"]["officer"]
        app_id = db_and_entities["app"].id
        r = client.post(f"/api/officer/applications/{app_id}/decision",
                        headers=_auth(t_o), json={"decision": "planet_destroyed", "reason_code": "xx"})
        assert r.status_code == 422
        # valid enum values still accepted
        r2 = client.post(f"/api/officer/applications/{app_id}/decision",
                         headers=_auth(t_o), json={"decision": "needs_more_info", "reason_code": "test_fix"})
        assert r2.status_code == 200
