"""
Financial Stress Simulator API routes.

Access control:
  - Applicants: may access ONLY stress analysis for their own applications.
  - Officers: may access stress analysis for any application (review context).
  - Config viewing: any authenticated user (transparency).
  - Config modification, history and officer assessments: officers only.

Isolation guarantee: no endpoint here ever writes hypothetical values into
Application records.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
from backend.core.auth import get_current_user, require_officer
from backend.services.financial_stress import service as stress_service
from backend.services.financial_stress.schemas import (
    CustomScenarioRequest,
    ProjectionRequest,
    OfficerAssessmentRequest,
    DEFAULT_STRESS_CONFIG,
)

router = APIRouter(prefix="/stress", tags=["Financial Stress Simulator"])


def _resolve_access(db: Session, application_id: str, user: User):
    try:
        return stress_service.get_authorized_application(db, application_id, user)
    except LookupError:
        raise HTTPException(status_code=404, detail="Application not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------------------------------------------------------------------------
# Configuration (admin management; transparent read)
# ---------------------------------------------------------------------------

@router.get("/config/default")
def get_default_config(current_user: User = Depends(get_current_user)):
    """Documented default configuration (full transparency)."""
    return DEFAULT_STRESS_CONFIG


@router.get("/config/history")
def get_admin_config_history(
    limit: int = 20,
    current_user: User = Depends(require_officer),
    db: Session = Depends(get_db),
):
    return {"history": stress_service.get_config_history(db, limit=limit)}


@router.get("/config")
def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return stress_service.get_active_config(db)


@router.put("/config")
def put_config(
    payload: dict,
    current_user: User = Depends(require_officer),
    db: Session = Depends(get_db),
):
    """Officer/admin update of simulation configuration; stores a new version."""
    note = payload.pop("_note", None) if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=422, detail="Configuration payload must be a non-empty object")
    try:
        result = stress_service.update_config(db, payload, updated_by=current_user.email, note=note)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {e}")
    return result


# ---------------------------------------------------------------------------
# Analysis endpoints
# ---------------------------------------------------------------------------

@router.get("/applications/{application_id}/baseline")
def get_baseline(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = _resolve_access(db, application_id, current_user)
    config = stress_service.get_active_config(db)
    baseline = stress_service.compute_baseline(app, config)
    return {
        "application_id": app.id,
        "calc_version": baseline["calc_version"],
        "inputs": baseline["inputs"],
        "metrics": {
            k: v for k, v in baseline.items()
            if k not in ("inputs", "calc_version")
        },
    }


@router.get("/applications/{application_id}/scenarios")
def get_predefined_scenarios(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = _resolve_access(db, application_id, current_user)
    return stress_service.run_full_simulation(db, app)


@router.post("/applications/{application_id}/custom")
def run_custom_scenario(
    application_id: str,
    req: CustomScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = _resolve_access(db, application_id, current_user)
    config = stress_service.get_active_config(db)
    result = stress_service.run_custom_application_scenario(app, req, config)
    result["application_id"] = app.id
    result["hypothetical"] = True
    return result


@router.post("/applications/{application_id}/projection")
def run_projection(
    application_id: str,
    req: ProjectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = _resolve_access(db, application_id, current_user)
    config = stress_service.get_active_config(db)
    result = stress_service.run_application_projection(app, req, config)
    result["application_id"] = app.id
    result["hypothetical"] = True
    return result


@router.get("/applications/{application_id}/report")
def export_report(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full scenario report (audit-logged)."""
    app = _resolve_access(db, application_id, current_user)
    return stress_service.export_stress_report(db, app, current_user)


@router.post("/applications/{application_id}/assessment")
def record_assessment(
    application_id: str,
    req: OfficerAssessmentRequest,
    current_user: User = Depends(require_officer),
    db: Session = Depends(get_db),
):
    """Officer-only advisory assessment record; never auto-approves/rejects."""
    app = _resolve_access(db, application_id, current_user)
    return stress_service.record_officer_assessment(db, app, current_user, req.assessment_note)
