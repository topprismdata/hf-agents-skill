#!/usr/bin/env python3
"""run.py — Start a local coding agent (llama-server + Pi).

Usage:
    python3 run.py                           # Interactive: choose model and start
    python3 run.py --model qwen              # Use Qwen model (fuzzy match)
    python3 run.py --model 1                 # Use recommendation #1 from hardware.py
    python3 run.py --port 8081               # Use specific port
    python3 run.py --task "写一个快排"        # Non-interactive: send task to Pi
    python3 run.py --model qwen --task "fix the bug in main.py"
"""

import argparse
import glob
import json
import os
import platform
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# ── Configuration ─────────────────────────────────────────────────

HF_CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")
DEFAULT_PORT = 8080
SERVER_READY_TIMEOUT = 120  # seconds to wait for llama-server to start
PI_CONFIG_DIR = os.path.expanduser("~/.config/pi")
PI_CONFIG_BACKUP = os.path.expanduser("~/.config/pi/config.json.bak")

# Popular coding models with their GGUF repo IDs
POPULAR_MODELS = {
    "qwen": {
        "7b": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "14b": "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        "32b": "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        "default": "7b",
    },
    "phi": {
        "4mini": "microsoft/Phi-4-mini-instruct-gguf",
        "default": "4mini",
    },
    "deepseek": {
        "6.7b": "TheBloke/deepseek-coder-6.7B-instruct-GGUF",
        "default": "6.7b",
    },
    "gemma": {
        "4b": "bartowski/gemma-3-4b-it-GGUF",
        "12b": "bartowski/gemma-3-12b-it-GGUF",
        "default": "4b",
    },
    "llama": {
        "8b": "bartowski/Llama-3.1-8B-Instruct-GGUF",
        "default": "8b",
    },
}


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, returning the CompletedProcess."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def log(msg: str):
    print(f"[hfa] {msg}", flush=True)


def check_server_running(port: int) -> bool:
    """Check if llama-server is already running on the given port."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health")
        resp = urllib.request.urlopen(req, timeout=2)
        return resp.status == 200
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        return False


def wait_for_server(port: int, timeout: int = SERVER_READY_TIMEOUT) -> bool:
    """Wait for llama-server to become ready."""
    start = time.time()
    while time.time() - start < timeout:
        if check_server_running(port):
            return True
        time.sleep(1)
    return False


def find_model_file(model_name: str) -> Optional[str]:
    """Search HuggingFace cache for a GGUF model file matching the name."""
    # Search in HF cache
    pattern = os.path.join(HF_CACHE_DIR, f"models--{model_name.replace('/', '--')}", "**", "*.gguf")
    matches = glob.glob(pattern, recursive=True)
    if matches:
        # Prefer Q4_K_M or Q5_K_M quantizations
        for preferred in ["Q4_K_M", "Q5_K_M", "Q4_K_S", "Q4_0", "Q5_0"]:
            for m in matches:
                if preferred in os.path.basename(m):
                    return m
        return matches[0]

    # Also check common download locations
    for download_dir in [
        os.path.expanduser("~/models"),
        os.path.expanduser("~/Downloads"),
        "/tmp/models",
    ]:
        if os.path.isdir(download_dir):
            for f in Path(download_dir).rglob("*.gguf"):
                if model_name.lower() in str(f).lower():
                    return str(f)

    return None


def download_model(model_id: str, quant_filter: str = "*Q4_K_M*") -> Optional[str]:
    """Download a model from HuggingFace Hub."""
    log(f"Downloading model: {model_id}")
    mirror = os.environ.get("HF_ENDPOINT", "")
    if mirror:
        log(f"Using mirror: {mirror}")

    cmd = ["hf", "download", model_id, "--include", quant_filter]
    result = run_cmd(cmd)
    if result.returncode != 0:
        # Try without quant filter (download all)
        log("Retrying without quantization filter...")
        cmd = ["hf", "download", model_id]
        result = run_cmd(cmd, timeout=600)

    if result.returncode == 0:
        # Output is the directory path
        download_dir = result.stdout.strip().split("\n")[-1]
        if download_dir and os.path.isdir(download_dir):
            gguf_files = list(Path(download_dir).rglob("*.gguf"))
            if gguf_files:
                return str(gguf_files[0])

    log(f"Download failed: {result.stderr}")
    return None


def resolve_model(model_arg: Optional[str]) -> Optional[str]:
    """Resolve a model argument (name, shortcut, or number) to a GGUF file path."""
    if model_arg is None:
        return None

    # If it's a number, look up from hardware recommendations
    if model_arg.isdigit():
        # Import hardware module to get recommendations
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, script_dir)
        try:
            from hardware import get_hf_recommendations, get_system_info, print_recommendations
            recs = get_hf_recommendations()
            if recs:
                idx = int(model_arg) - 1
                if 0 <= idx < len(recs):
                    rec = recs[idx]
                    model_id = rec.get("model_id", rec.get("name", ""))
                    if model_id:
                        return resolve_model(model_id)
        except Exception:
            pass
        log(f"Could not resolve recommendation #{model_arg}")
        return None

    # Check if it's a direct path to a GGUF file
    if os.path.isfile(model_arg) and model_arg.endswith(".gguf"):
        return model_arg

    # Check if it's a HuggingFace model ID (contains /)
    if "/" in model_arg:
        # First check cache
        cached = find_model_file(model_arg)
        if cached:
            log(f"Found cached model: {cached}")
            return cached
        # Download it
        return download_model(model_arg)

    # Check if it's a shortcut name (qwen, phi, deepseek, etc.)
    model_lower = model_arg.lower()
    if model_lower in POPULAR_MODELS:
        model_info = POPULAR_MODELS[model_lower]
        default_size = model_info["default"]
        model_id = model_info[default_size]
        log(f"Resolved '{model_arg}' -> {model_id}")

        # Check cache first
        cached = find_model_file(model_id)
        if cached:
            log(f"Found cached: {cached}")
            return cached
        return download_model(model_id)

    # Try fuzzy match against popular models
    for key, info in POPULAR_MODELS.items():
        if key in model_lower or model_lower in key:
            model_id = info[info["default"]]
            log(f"Resolved '{model_arg}' -> {model_id}")
            cached = find_model_file(model_id)
            if cached:
                return cached
            return download_model(model_id)

    # Last resort: treat as a HuggingFace model ID
    log(f"Treating '{model_arg}' as a HuggingFace model ID")
    return download_model(model_arg)


def start_llama_server(model_path: str, port: int) -> Optional[subprocess.Popen]:
    """Start llama-server with the given model."""
    # Build command
    cmd = ["llama-server", "-m", model_path, "--port", str(port), "--host", "0.0.0.0"]

    # Apple Silicon: use Metal
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        cmd.extend(["-ngl", "99"])  # offload all layers to GPU
    elif platform.system() == "Linux":
        # Check for NVIDIA GPU
        result = run_cmd(["nvidia-smi"])
        if result.returncode == 0:
            cmd.extend(["-ngl", "99"])

    # Context size for coding tasks
    cmd.extend(["-c", "8192"])

    log(f"Starting llama-server: {' '.join(cmd)}")
    log(f"  Model: {model_path}")
    log(f"  Port:  {port}")

    # Redirect output to log file
    log_dir = os.path.expanduser("~/.cache/hf-agents")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "llama-server.log")
    log_file = open(log_path, "w")

    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # detach from parent
        close_fds=True,  # ensure clean file descriptor inheritance
    )

    log(f"Waiting for server to be ready (PID: {proc.pid})...")
    if wait_for_server(port):
        log_file.close()  # release handle; server has its own fd
        log(f"Server is ready at http://localhost:{port}")
        return proc
    else:
        log_file.close()
        log("Server failed to start within timeout. Check logs:")
        log(f"  tail -50 {log_path}")
        proc.terminate()
        return None


def start_pi(port: int, task: Optional[str] = None) -> Optional[subprocess.Popen]:
    """Start the Pi coding agent."""
    # Check if Pi (hf agents run pi) is available
    result = run_cmd(["hf", "extensions", "exec", "agents", "run", "pi", "--help"])
    if result.returncode != 0:
        result = run_cmd(["hf", "agents", "run", "pi", "--help"])

    if result.returncode != 0:
        log("Pi agent not available. Starting interactive chat with llama-server instead.")
        log(f"Connect to: http://localhost:{port}")
        log("Or use curl to interact with the API:")
        log(f'  curl http://localhost:{port}/v1/chat/completions -d \'{{"messages":[{{"role":"user","content":"Hello"}}]}}\'')
        return None

    # Set Pi config to point to our llama-server
    os.makedirs(PI_CONFIG_DIR, exist_ok=True)
    config_path = os.path.join(PI_CONFIG_DIR, "config.json")

    # Backup existing config
    if os.path.exists(config_path):
        import shutil
        shutil.copy2(config_path, PI_CONFIG_BACKUP)

    config = {
        "api_base": f"http://localhost:{port}/v1",
        "model": "local",
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    # Build Pi command
    cmd = ["hf", "extensions", "exec", "agents", "run", "pi", "--top", "5"]
    if task:
        cmd.extend(["--task", task])

    log(f"Starting Pi agent: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)

    return proc


def main():
    parser = argparse.ArgumentParser(description="Start a local coding agent")
    parser.add_argument("--model", "-m", help="Model name, shortcut (qwen/phi/deepseek), or recommendation number")
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    parser.add_argument("--task", "-t", help="Non-interactive task to send to Pi")
    parser.add_argument("--skip-server", action="store_true", help="Skip llama-server startup (already running)")
    args = parser.parse_args()

    # Check if server is already running
    if check_server_running(args.port):
        log(f"llama-server is already running on port {args.port}")
        if args.task:
            proc = start_pi(args.port, args.task)
            if proc:
                proc.wait()
        else:
            log("Connect to Pi or use the API directly.")
        return

    # Need to start server — must have a model
    if args.skip_server:
        log("Server not running and --skip-server specified. Exiting.")
        sys.exit(1)

    model_path = resolve_model(args.model)

    if not model_path:
        if args.model:
            log(f"Could not resolve model: {args.model}")
        log("\nNo model specified. Options:")
        log("  --model qwen       Use Qwen2.5-Coder-7B (recommended)")
        log("  --model phi        Use Phi-4-mini")
        log("  --model deepseek   Use DeepSeek-Coder-6.7B")
        log("  --model <hf/id>    Use specific HuggingFace model ID")
        log("  --model 1          Use recommendation #1 from hardware.py")
        log("\nRun 'python3 hardware.py --recommend-only' to see recommendations.")
        sys.exit(1)

    # Start llama-server
    server_proc = start_llama_server(model_path, args.port)
    if not server_proc:
        sys.exit(1)

    # Start Pi agent
    pi_proc = start_pi(args.port, args.task)

    if pi_proc:
        try:
            pi_proc.wait()
        except KeyboardInterrupt:
            log("\nStopping Pi...")
            pi_proc.terminate()

    log("Done. llama-server is still running in the background.")
    log(f"  Stop it with: python3 {os.path.abspath(__file__).replace('run.py', 'stop.sh')}")


if __name__ == "__main__":
    main()
