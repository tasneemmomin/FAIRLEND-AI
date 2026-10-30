import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
MODEL_DIR = DATA_DIR / "models"

# Ensure runtime directories exist
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    APP_NAME: str = "LoanLens"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'loanlens.db'}"

    # Paths
    BASE_DIR: Path = BASE_DIR
    CONFIG_DIR: Path = CONFIG_DIR
    DATA_DIR: Path = DATA_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    MODEL_DIR: Path = MODEL_DIR

    # Encryption / Security
    SECRET_KEY: str = "loanlens-insecure-default-change-me"
    ENCRYPTION_KEY_FILE: Path = DATA_DIR / "loanlens.key"

    # Stage 2 -> Stage 3 Online Model Activation Thresholds
    STAGE_ACTIVATION_MIN_LABELS: int = 100
    STAGE_ACTIVATION_MIN_PER_CLASS: int = 20
    SHADOW_MODE_EVAL_WINDOW: int = 50
    SHADOW_PROMOTION_MIN_AGREEMENT: float = 0.80
    SHADOW_PROMOTION_MAX_BRIER: float = 0.25

    # Voice / Whisper
    WHISPER_MODEL_SIZE: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    STORE_RAW_AUDIO: bool = False  # Consent & retention: only transcripts stored

    # Policy rules file
    POLICY_RULES_FILE: Path = CONFIG_DIR / "policy_rules.yaml"
    PHRASE_DICTIONARY_FILE: Path = CONFIG_DIR / "phrase_dictionary.yaml"
    IMMUTABLE_FEATURES_FILE: Path = CONFIG_DIR / "immutable_features.yaml"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
