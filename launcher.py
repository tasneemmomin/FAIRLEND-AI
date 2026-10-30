import argparse
import hashlib
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Suppress harmless symlink warnings on standard Windows accounts
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / ".venv"
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"
HASH_FILE = VENV_DIR / "requirements.sha256"
FRONTEND_DIR = BASE_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

def get_python_exe() -> Path:
    if os.name == "nt":
        exe = VENV_DIR / "Scripts" / "python.exe"
    else:
        exe = VENV_DIR / "bin" / "python"
    return exe

def compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def is_python_valid(exe: Path) -> bool:
    if not exe.exists():
        return False
    try:
        subprocess.check_call([str(exe), "-c", "import sys"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def ensure_venv():
    python_exe = get_python_exe()
    if not is_python_valid(python_exe):
        print(f"[LoanLens] Creating virtual environment at {VENV_DIR}...")
        subprocess.check_call([sys.executable, "-m", "venv", "--system-site-packages", "--clear", str(VENV_DIR)])
    return python_exe

def ensure_dependencies(python_exe: Path):
    if not REQUIREMENTS_FILE.exists():
        return
    current_hash = compute_file_hash(REQUIREMENTS_FILE)
    if HASH_FILE.exists() and HASH_FILE.read_text().strip() == current_hash:
        print("[LoanLens] Python dependencies up to date.")
        return

    print("[LoanLens] Installing / updating Python requirements...")
    cmd = [str(python_exe), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)]
    try:
        subprocess.check_call(cmd)
        HASH_FILE.write_text(current_hash)
        print("[LoanLens] Python dependencies successfully installed.")
    except Exception as e:
        print(f"[LoanLens Warning] Error updating requirements: {e}. Continuing with existing packages.")

def ensure_speech_model(skip_speech: bool = False):
    """Attempts to pre-cache the faster-whisper base model or safely falls back."""
    if skip_speech:
        print("[LoanLens] Speech model download skipped (--skip-speech flag).", flush=True)
        print("[LoanLens] The applicant portal will use the browser typed-input intake fallback.", flush=True)
        return

    print("[LoanLens] Checking speech-to-text model (faster-whisper base)...", flush=True)
    model_dir = BASE_DIR / "data" / "models"
    has_local = any(model_dir.glob("*.bin")) or any(model_dir.glob("*.onnx")) or any(model_dir.glob("*model*"))

    online = False
    try:
        req = urllib.request.Request("https://huggingface.co", headers={"User-Agent": "LoanLens"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                online = True
    except Exception:
        online = False

    if not online and not has_local:
        print("[LoanLens Notice] Speech model download postponed (offline/local mode).", flush=True)
        print("[LoanLens] The applicant portal will use the browser typed-input fallback automatically.", flush=True)
        return

    try:
        from faster_whisper import WhisperModel
        print("[LoanLens] Downloading / loading Whisper model on CPU (int8)...", flush=True)
        if not has_local:
            print("[LoanLens] First-time model download (~140MB) takes ~30-60 seconds depending on connection. Please wait...", flush=True)
        model = WhisperModel("base", device="cpu", compute_type="int8", download_root=str(model_dir))
        print("[LoanLens] Speech model ready.", flush=True)
    except Exception as e:
        print(f"[LoanLens Notice] Speech model download postponed or offline ({e}).", flush=True)
        print("[LoanLens] The applicant portal will use the browser typed-input fallback automatically.", flush=True)

def ensure_frontend():
    """Checks whether the frontend bundle is built. Builds it if missing."""
    if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
        print("[LoanLens] Frontend production bundle found.")
        return

    print("[LoanLens] Building frontend production bundle...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    try:
        # Check node_modules
        if not (FRONTEND_DIR / "node_modules").exists():
            print("[LoanLens] Installing frontend npm dependencies...")
            subprocess.check_call([npm_cmd, "install"], cwd=str(FRONTEND_DIR))
        print("[LoanLens] Compiling Vite frontend...")
        subprocess.check_call([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR))
        print("[LoanLens] Frontend built successfully.")
    except Exception as e:
        print(f"[LoanLens Warning] Frontend build failed or npm not accessible: {e}.")
        print("[LoanLens] If running in developer mode, please build frontend or run vite dev server.")

def wait_for_health(port: int, timeout: int = 30) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LoanLens-Launcher"})
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    parser = argparse.ArgumentParser(description="FairLendAI Launcher")
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on")
    parser.add_argument("--reset-db", action="store_true", help="Reset/drop database tables on start")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--officer-only", action="store_true", help="Open only the officer dashboard in browser")
    parser.add_argument("--skip-speech", action="store_true", help="Skip speech model download and use typed intake")
    args = parser.parse_args()

    print("=" * 70)
    print("  FairLendAI - Explainable Credit Assessment Platform")
    print("  Final-Year B.Tech Capstone Project in Artificial Intelligence & Data Science")
    print("  Explainable AI | Document Intelligence | Fairness Monitoring")
    print("=" * 70)

    python_exe = ensure_venv()
    ensure_dependencies(python_exe)

    if args.reset_db:
        print("[FairLendAI] Resetting database tables as requested...")
        cmd = [str(python_exe), "-c", "from backend.db.session import reset_db; reset_db(); print('Database reset completed.')"]
        subprocess.check_call(cmd)
    else:
        print("[FairLendAI] Initializing database schema...")
        cmd = [str(python_exe), "-c", "from backend.db.session import init_db; init_db(); print('Database schema ready.')"]
        subprocess.check_call(cmd)

    ensure_speech_model(args.skip_speech)
    ensure_frontend()

    print(f"[FairLendAI] Starting FastAPI backend on http://127.0.0.1:{args.port}...")
    server_cmd = [
        str(python_exe),
        "-m", "uvicorn",
        "backend.api.app:app",
        "--host", "127.0.0.1",
        "--port", str(args.port)
    ]

    server_process = subprocess.Popen(server_cmd)

    try:
        print("[FairLendAI] Waiting for server healthcheck...")
        if wait_for_health(args.port):
            print(f"[FairLendAI] Server is healthy and listening on http://127.0.0.1:{args.port}")
            applicant_url = f"http://127.0.0.1:{args.port}/"
            officer_url = f"http://127.0.0.1:{args.port}/#officer"

            if not args.no_browser:
                if args.officer_only:
                    print(f"[FairLendAI] Opening Officer Dashboard: {officer_url}")
                    webbrowser.open(officer_url)
                else:
                    print(f"[FairLendAI] Opening FairLendAI Landing Page: {applicant_url}")
                    webbrowser.open(applicant_url)

            print("[FairLendAI] Application running. Press Ctrl+C in this terminal to stop.")
            server_process.wait()
        else:
            print("[FairLendAI Error] Server failed to respond to healthcheck within timeout.")
            server_process.terminate()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[FairLendAI] Shutting down server gracefully...")
        server_process.terminate()
        server_process.wait()
        print("[FairLendAI] Stopped.")

if __name__ == "__main__":
    main()
