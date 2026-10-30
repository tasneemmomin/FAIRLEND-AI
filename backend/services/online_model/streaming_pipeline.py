import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import river
from river import preprocessing, tree, drift
from backend.core.config import settings
from backend.db.database import SessionLocal
from backend.db.models import Application, OfficerDecision, SystemDriftEvent

MODEL_FILE = settings.MODEL_DIR / "river_pipeline.pkl"
DRIFT_FILE = settings.MODEL_DIR / "river_drift.pkl"

class OnlineModelManager:
    def __init__(self):
        self.model = self._load_or_create_model()
        self.drift_detector = self._load_or_create_drift_detector()
        self.recent_evaluations = []  # Stores tuple of (prob_approval, officer_binary, agreed)
        self.is_promoted = False

    def _load_or_create_model(self):
        if MODEL_FILE.exists():
            try:
                with open(MODEL_FILE, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        # Default River pipeline: Scaler + Hoeffding Adaptive Tree Classifier
        pipeline = preprocessing.StandardScaler() | tree.HoeffdingAdaptiveTreeClassifier(
            grace_period=20,
            split_criterion='gini',
            delta=1e-4
        )
        return pipeline

    def _load_or_create_drift_detector(self):
        if DRIFT_FILE.exists():
            try:
                with open(DRIFT_FILE, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        return drift.ADWIN(delta=0.002)

    def save(self):
        settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(MODEL_FILE, "wb") as f:
                pickle.dump(self.model, f)
            with open(DRIFT_FILE, "wb") as f:
                pickle.dump(self.drift_detector, f)
        except Exception:
            pass

    def prepare_features(self, feat_vec: Dict[str, Any]) -> Dict[str, float]:
        """Flattens and encodes feature vector into numerical river features."""
        x = {}
        for k, v in feat_vec.items():
            if isinstance(v, (int, float)):
                x[k] = float(v)
            elif isinstance(v, str):
                # Basic one-hot / frequency mapping for string categories
                x[f"{k}_{v}"] = 1.0
        return x

    def predict_one(self, feat_vec: Dict[str, Any]) -> Tuple[float, str]:
        """
        Returns (prob_approval, predicted_class).
        If model hasn't learned any classes yet, defaults to (0.5, 'needs_review').
        """
        x = self.prepare_features(feat_vec)
        try:
            probas = self.model.predict_proba_one(x)
            prob_approve = probas.get(True, 0.5)
            if prob_approve >= 0.65:
                pred = "likely_approved"
            elif prob_approve <= 0.35:
                pred = "unlikely_approved"
            else:
                pred = "needs_review"
            return float(prob_approve), pred
        except Exception:
            return 0.5, "needs_review"

    def handle_officer_decision(self, app: Application, decision: str):
        """
        Incremental learning step (`learn_one`).
        Triggered when an officer approves or rejects an application.
        """
        # Only binary approve/reject are direct training labels
        if decision not in ("approve", "reject"):
            return

        y_true = (decision == "approve")
        feat_vec = app.feature_snapshots[0].feature_vector if app.feature_snapshots else {}
        if not feat_vec:
            return

        x = self.prepare_features(feat_vec)

        # 1. Prequential prediction before updating (Test-then-train protocol)
        try:
            probas = self.model.predict_proba_one(x)
            prob_approve = probas.get(True, 0.5)
            predicted_approval = (prob_approve >= 0.5)
            model_agreed = (predicted_approval == y_true)
            loss = 0.0 if model_agreed else 1.0
        except Exception:
            prob_approve = 0.5
            model_agreed = False
            loss = 1.0

        # Record for rolling agreement and Brier calibration
        self.recent_evaluations.append((prob_approve, 1.0 if y_true else 0.0, model_agreed))
        if len(self.recent_evaluations) > settings.SHADOW_MODE_EVAL_WINDOW:
            self.recent_evaluations.pop(0)

        # 2. ADWIN Drift Detection update
        self.drift_detector.update(loss)
        if self.drift_detector.drift_detected:
            self._record_drift_event(loss)

        # 3. Incremental update: learn_one
        self.model.learn_one(x, y_true)
        self.save()

        # Check promotion gate
        self._check_promotion_gates()

    def _record_drift_event(self, metric_val: float):
        db = SessionLocal()
        try:
            total_decisions = db.query(OfficerDecision).count()
            event = SystemDriftEvent(
                detector_name="ADWIN_ConceptDrift",
                metric_value=metric_val,
                message="Concept drift detected in officer decision stream. Model adaptation triggered.",
                total_cases_at_drift=total_decisions
            )
            db.add(event)
            db.commit()
        except Exception:
            pass
        finally:
            db.close()

    def _check_promotion_gates(self):
        """Checks if shadow model meets agreement and calibration gates for active promotion."""
        if len(self.recent_evaluations) < 20:
            self.is_promoted = False
            return

        agreements = sum(1 for _, _, agreed in self.recent_evaluations)
        agreement_rate = agreements / len(self.recent_evaluations)
        brier_score = sum((p - y) ** 2 for p, y, _ in self.recent_evaluations) / len(self.recent_evaluations)

        if (agreement_rate >= settings.SHADOW_PROMOTION_MIN_AGREEMENT and
            brier_score <= settings.SHADOW_PROMOTION_MAX_BRIER):
            self.is_promoted = True
        else:
            self.is_promoted = False

    def get_shadow_stats(self) -> Dict[str, Any]:
        if not self.recent_evaluations:
            return {
                "rolling_window": len(self.recent_evaluations),
                "agreement_rate": None,
                "brier_score": None,
                "is_promoted": False
            }
        agreements = sum(1 for _, _, agreed in self.recent_evaluations)
        agreement_rate = round(agreements / len(self.recent_evaluations), 3)
        brier_score = round(sum((p - y) ** 2 for p, y, _ in self.recent_evaluations) / len(self.recent_evaluations), 4)

        return {
            "rolling_window": len(self.recent_evaluations),
            "agreement_rate": agreement_rate,
            "brier_score": brier_score,
            "is_promoted": self.is_promoted
        }

online_model_manager = OnlineModelManager()
