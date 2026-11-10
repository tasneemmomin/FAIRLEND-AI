import re
from pathlib import Path
import pytest
from backend.core.config import settings
from backend.db.database import SessionLocal
from backend.api.routes.health import get_system_health
from backend.api.routes.privacy import get_regulatory_disclosures
from backend.api.app import app

def test_health_endpoint_logic():
    db = SessionLocal()
    data = get_system_health(db)
    db.close()
    assert data["status"] == "healthy"
    assert data["app_name"] == "LoanLens"
    assert "stage" in data["current_stage"]

def test_regulatory_disclosures():
    data = get_regulatory_disclosures()
    assert "prototype_disclaimer" in data
    assert "DPDP" in data["dpdp_notice"]
    assert "Recommendations" in data["final_decision_maker_notice"]

def test_frontend_dist_bundle():
    dist_dir = settings.BASE_DIR / "frontend" / "dist"
    index_html = dist_dir / "index.html"
    assert index_html.exists(), "Compiled frontend index.html must exist in frontend/dist"
    
    html_content = index_html.read_text(encoding="utf-8")
    assert "LoanLens" in html_content
    assert "/assets/" in html_content

    # Check asset files exist
    assets_dir = dist_dir / "assets"
    assert assets_dir.exists()
    asset_files = list(assets_dir.glob("index-*.js"))
    assert len(asset_files) > 0, "Compiled JavaScript bundle must exist in frontend/dist/assets"

def test_api_route_registrations():
    route_paths = list(app.openapi()["paths"].keys())
    expected = [
        "/api/health",
        "/api/intake/submit",
        "/api/intake/{application_id}",
        "/api/officer/applications",
        "/api/documents/upload",
        "/api/voice/init",
        "/api/voice/turn",
        "/api/explain/{application_id}",
        "/api/fairness/metrics",
        "/api/privacy/disclosures",
        # Financial Stress Early-Warning & Future Scenario Intelligence
        "/api/stress/applications/{application_id}/baseline",
        "/api/stress/applications/{application_id}/scenarios",
        "/api/stress/applications/{application_id}/custom",
        "/api/stress/applications/{application_id}/projection",
        "/api/stress/applications/{application_id}/report",
        "/api/stress/applications/{application_id}/assessment",
        "/api/stress/config"
    ]
    for exp in expected:
        assert exp in route_paths, f"Expected API route {exp} not registered in FastAPI app"
