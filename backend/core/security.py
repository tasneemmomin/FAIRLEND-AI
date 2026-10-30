import os
from pathlib import Path
from cryptography.fernet import Fernet
from backend.core.config import settings

_fernet_instance = None

def get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        key_file = settings.ENCRYPTION_KEY_FILE
        if key_file.exists():
            key = key_file.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(key)
        _fernet_instance = Fernet(key)
    return _fernet_instance

def encrypt_field(plain_text: str | None) -> str | None:
    if plain_text is None:
        return None
    f = get_fernet()
    return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_field(cipher_text: str | None) -> str | None:
    if cipher_text is None:
        return None
    f = get_fernet()
    try:
        return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback in case of raw or corrupted text
        return cipher_text

def mask_sensitive(text: str | None, visible_chars: int = 4) -> str:
    if not text:
        return ""
    if len(text) <= visible_chars:
        return "*" * len(text)
    return text[:visible_chars] + "*" * (len(text) - visible_chars)
