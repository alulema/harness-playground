import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
PORT = os.getenv("PORT", "8080")


def wait_for_ollama(process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Ollama exited during startup with status {process.returncode}.")
        try:
            with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2):
                return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise RuntimeError("Ollama did not become ready within 120 seconds.")


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    ollama = subprocess.Popen(["ollama", "serve"])
    api: subprocess.Popen[bytes] | None = None
    stopping = False

    def handle_signal(_: int, __: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        wait_for_ollama(ollama)
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "0.0.0.0",
                "--port",
                PORT,
            ]
        )
        while not stopping:
            if ollama.poll() is not None:
                return ollama.returncode or 1
            if api.poll() is not None:
                return api.returncode or 1
            time.sleep(0.5)
        return 0
    finally:
        if api is not None:
            stop(api)
        stop(ollama)


if __name__ == "__main__":
    sys.exit(main())
