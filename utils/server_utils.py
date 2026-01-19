import os,time,sys

def restart_app():
    time.sleep(2)
    os.execv(sys.executable, [
        sys.executable,
        "-m", "uvicorn",
        "app:app",
        "--reload"
    ])
