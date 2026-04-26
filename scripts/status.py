#!/usr/bin/env python3
"""status.py — Check status of llama-server and Pi agent.

Usage:
    python3 status.py
    python3 status.py --json
"""

import json
import os
import platform
import subprocess
import sys
import urllib.request
import urllib.error
from typing import Optional


LOG_DIR = os.path.expanduser("~/.cache/hf-agents")
LOG_FILE = os.path.join(LOG_DIR, "llama-server.log")
PI_CONFIG = os.path.expanduser("~/.config/pi/config.json")


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def check_llama_server(port: int = 8080) -> dict:
    """Check if llama-server is running and healthy."""
    info = {"running": False, "port": port}

    # Check by PID
    result = run_cmd(["pgrep", "-f", "llama-server"])
    if result.returncode == 0:
        pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        info["pids"] = pids
        info["pid_count"] = len(pids)
    else:
        # Try lsof for the port
        result = run_cmd(["lsof", "-i", f":{port}", "-t"])
        if result.returncode == 0:
            info["pids"] = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]

    # Health check
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health")
        resp = urllib.request.urlopen(req, timeout=3)
        info["running"] = True
        info["health"] = "ok"

        # Try to get model info from the server
        try:
            req2 = urllib.request.Request(f"http://localhost:{port}/props")
            resp2 = urllib.request.urlopen(req2, timeout=3)
            props = json.loads(resp2.read().decode())
            info["model"] = props.get("default_generation_settings", {}).get("model", "unknown")
        except Exception:
            pass

    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        info["health"] = "not responding"

    return info


def check_pi() -> dict:
    """Check if Pi agent is running."""
    info = {"running": False}

    result = run_cmd(["pgrep", "-f", "hf.*agents.*run.*pi"])
    if result.returncode != 0:
        result = run_cmd(["pgrep", "-f", "pi-agent"])
    if result.returncode == 0:
        pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        info["running"] = True
        info["pids"] = pids

    # Check Pi config
    if os.path.exists(PI_CONFIG):
        try:
            with open(PI_CONFIG) as f:
                config = json.load(f)
            info["config"] = config
        except (json.JSONDecodeError, OSError):
            pass

    return info


def get_memory_usage(pid: str) -> Optional[str]:
    """Get memory usage for a PID."""
    result = run_cmd(["ps", "-o", "rss=", "-p", pid])
    if result.returncode == 0 and result.stdout.strip():
        rss_kb = int(result.stdout.strip())
        if rss_kb > 1024 * 1024:
            return f"{rss_kb / (1024*1024):.1f} GB"
        else:
            return f"{rss_kb / 1024:.0f} MB"
    return None


def get_tail_log(lines: int = 20) -> Optional[str]:
    """Get the last N lines of llama-server log."""
    if not os.path.exists(LOG_FILE):
        return None
    result = run_cmd(["tail", "-n", str(lines), LOG_FILE])
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def main():
    use_json = "--json" in sys.argv

    # Check ports 8080-8089
    server_status = None
    for port in range(8080, 8090):
        status = check_llama_server(port)
        if status["running"]:
            server_status = status
            break

    if not server_status:
        server_status = check_llama_server(8080)

    pi_status = check_pi()

    if use_json:
        output = {
            "llama_server": server_status,
            "pi": pi_status,
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print("=" * 50)
    print("  hf-agents Status")
    print("=" * 50)

    # llama-server
    print("\nllama-server:")
    if server_status["running"]:
        print(f"  Status:  Running on port {server_status['port']}")
        if "model" in server_status:
            print(f"  Model:   {server_status['model']}")
        if "pids" in server_status:
            for pid in server_status["pids"]:
                mem = get_memory_usage(pid)
                mem_str = f" ({mem})" if mem else ""
                print(f"  PID:     {pid}{mem_str}")
    else:
        print("  Status:  Not running")

    # Pi agent
    print("\nPi agent:")
    if pi_status["running"]:
        print(f"  Status:  Running")
        if "pids" in pi_status:
            for pid in pi_status["pids"]:
                mem = get_memory_usage(pid)
                mem_str = f" ({mem})" if mem else ""
                print(f"  PID:     {pid}{mem_str}")
    else:
        print("  Status:  Not running")

    if "config" in pi_status:
        print(f"  API:     {pi_status['config'].get('api_base', 'unknown')}")

    # Log tail (if server has errors or not running)
    log_tail = get_tail_log(10)
    if log_tail:
        print(f"\nllama-server log (last 10 lines):")
        for line in log_tail.split("\n"):
            print(f"  {line}")

    print()


if __name__ == "__main__":
    main()
