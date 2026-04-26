#!/usr/bin/env python3
"""diagnose.py — Diagnose and fix common hf-agents issues.

Usage:
    python3 diagnose.py
    python3 diagnose.py --fix   # Attempt automatic fixes
"""

import json
import os
import platform
import socket
import subprocess
import sys
import urllib.request
import urllib.error
from typing import Optional


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def log(msg: str, level: str = "info"):
    icons = {"ok": "[OK]", "warn": "[WARN]", "fail": "[FAIL]", "info": "[INFO]", "fix": "[FIX]"}
    print(f"{icons.get(level, '[??]')} {msg}")


class Diagnostic:
    def __init__(self, auto_fix: bool = False):
        self.auto_fix = auto_fix
        self.issues = []

    def check(self, name: str) -> bool:
        """Register a check. Returns True if issue found."""
        self.current_check = name
        return True

    def issue(self, desc: str, fix: str = "", fix_cmd: list = None):
        """Report an issue."""
        self.issues.append(f"{self.current_check}: {desc}" + (f" → {fix}" if fix else ""))
        log(f"{self.current_check}: {desc}", "fail")
        if fix:
            log(f"  Suggested fix: {fix}", "warn")
        if self.auto_fix and fix_cmd:
            log(f"  Attempting auto-fix...", "fix")
            result = run_cmd(fix_cmd)
            if result.returncode == 0:
                log(f"  Auto-fix succeeded.", "ok")
            else:
                log(f"  Auto-fix failed: {result.stderr}", "fail")

    def ok(self, msg: str):
        log(f"{self.current_check}: {msg}", "ok")


def diagnose_all(auto_fix: bool = False) -> list:
    diag = Diagnostic(auto_fix)
    issues = []

    # ── 1. Check llama-server binary ─────────────────────────────
    diag.check("llama-server binary")
    result = run_cmd(["which", "llama-server"])
    if result.returncode == 0:
        diag.ok(f"Found at {result.stdout.strip()}")
        # Check version
        vresult = run_cmd(["llama-server", "--version"])
        if vresult.returncode == 0:
            diag.ok(f"Version: {vresult.stdout.strip().split(chr(10))[0]}")
    else:
        diag.issue(
            "llama-server not found in PATH",
            fix="Install llama.cpp: brew install llama.cpp (macOS) or build from source",
            fix_cmd=["brew", "install", "llama.cpp"] if platform.system() == "Darwin" else None,
        )
        issues.append("llama-server not found")

    # ── 2. Check hf CLI ─────────────────────────────────────────
    diag.check("hf CLI")
    result = run_cmd(["which", "hf"])
    if result.returncode == 0:
        vresult = run_cmd(["hf", "--version"])
        diag.ok(f"Found: {vresult.stdout.strip() if vresult.returncode == 0 else 'version unknown'}")
    else:
        diag.issue(
            "hf CLI not found",
            fix="Install: pip install -U huggingface_hub",
            fix_cmd=["pip", "install", "-U", "huggingface_hub"],
        )
        issues.append("hf CLI not found")

    # ── 3. Check hf-agents extension ─────────────────────────────
    diag.check("hf-agents extension")
    result = run_cmd(["hf", "extensions", "list"])
    if result.returncode == 0 and "agents" in result.stdout:
        diag.ok("hf-agents extension is installed")
    else:
        diag.issue(
            "hf-agents extension not installed",
            fix="Install: hf extensions install hf-agents",
            fix_cmd=["hf", "extensions", "install", "hf-agents"] if auto_fix else None,
        )
        issues.append("hf-agents extension not installed")

    # ── 4. Check port availability ───────────────────────────────
    for port in [8080, 8081]:
        diag.check(f"Port {port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        if result == 0:
            # Check what's using it
            lresult = run_cmd(["lsof", "-i", f":{port}", "-P", "-n"])
            if lresult.returncode == 0:
                lines = lresult.stdout.strip().split("\n")
                process_info = lines[-1] if len(lines) > 0 else "unknown process"
                diag.issue(
                    f"Port {port} is in use",
                    fix=f"Stop the process or use --port to choose a different port. Currently: {process_info}",
                )
            else:
                diag.issue(f"Port {port} is in use by an unknown process")
        else:
            diag.ok(f"Port {port} is available")

    # ── 5. Check if llama-server is running ──────────────────────
    diag.check("llama-server status")
    try:
        req = urllib.request.Request("http://localhost:8080/health")
        resp = urllib.request.urlopen(req, timeout=3)
        if resp.status == 200:
            diag.ok("llama-server is running and healthy")
        else:
            diag.issue(f"llama-server returned status {resp.status}")
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        # Check if process exists but not responding
        result = run_cmd(["pgrep", "-f", "llama-server"])
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            diag.issue(
                f"llama-server process exists (PID: {', '.join(pids)}) but not responding on port 8080",
                fix="It may be using a different port or crashed. Check logs or kill it.",
            )
            if auto_fix:
                log("  Killing stale llama-server processes...", "fix")
                run_cmd(["pkill", "-f", "llama-server"])
        else:
            log("llama-server is not running (this is normal if you haven't started it)", "info")

    # ── 6. Check HuggingFace auth ────────────────────────────────
    diag.check("HuggingFace auth")
    token_file = os.path.expanduser("~/.cache/huggingface/token")
    hf_token = os.environ.get("HF_TOKEN", "")
    if os.path.exists(token_file) or hf_token:
        diag.ok("HuggingFace token is configured")
    else:
        diag.issue(
            "No HuggingFace token found",
            fix="Run 'hf login' or set HF_TOKEN environment variable (needed for gated models)",
        )

    # ── 7. Check memory ──────────────────────────────────────────
    diag.check("System memory")
    if platform.system() == "Darwin":
        result = run_cmd(["sysctl", "-n", "hw.memsize"])
        if result.returncode == 0:
            mem_gb = int(result.stdout.strip()) / (1024**3)
            diag.ok(f"Memory: {mem_gb:.1f} GB")
            if mem_gb < 8:
                diag.issue(
                    f"Only {mem_gb:.1f} GB RAM — most coding models need 8GB+",
                    fix="Consider small models like Phi-4-mini or use cloud-based alternatives",
                )
    elif platform.system() == "Linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        mem_kb = int(line.split()[1])
                        mem_gb = mem_kb / (1024**2)
                        diag.ok(f"Memory: {mem_gb:.1f} GB")
                        break
        except (FileNotFoundError, ValueError):
            pass

    # ── 8. Check for GPU support ─────────────────────────────────
    diag.check("GPU support")
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        diag.ok("Apple Silicon detected — Metal GPU acceleration available")
    else:
        result = run_cmd(["nvidia-smi"])
        if result.returncode == 0:
            # Parse GPU info
            for line in result.stdout.split("\n"):
                if "MiB" in line and "/" in line:
                    diag.ok(f"NVIDIA GPU detected: {line.strip()}")
                    break
            else:
                diag.ok("NVIDIA GPU detected")
        else:
            diag.issue(
                "No NVIDIA GPU detected — inference will run on CPU (slow)",
                fix="For better performance, use a machine with a GPU or Apple Silicon",
            )

    # ── 9. Check llama-server logs for errors ────────────────────
    diag.check("llama-server logs")
    log_file = os.path.expanduser("~/.cache/hf-agents/llama-server.log")
    if os.path.exists(log_file):
        result = run_cmd(["tail", "-20", log_file])
        if result.returncode == 0:
            errors = [l for l in result.stdout.split("\n") if "error" in l.lower() or "fail" in l.lower()]
            if errors:
                diag.issue(
                    f"Found {len(errors)} error line(s) in recent logs",
                    fix=f"Check full log: tail -100 {log_file}",
                )
                for err in errors[:3]:
                    print(f"    {err.strip()}")
            else:
                diag.ok("No errors in recent logs")
    else:
        log("No log file found (normal if server never started)", "info")

    # ── 10. Check jq, fzf, node ─────────────────────────────────
    for dep in ["jq", "fzf", "node"]:
        diag.check(dep)
        result = run_cmd(["which", dep])
        if result.returncode == 0:
            diag.ok(f"Found at {result.stdout.strip()}")
        else:
            diag.issue(
                f"{dep} not found",
                fix=f"Install {dep}: brew install {dep}" if platform.system() == "Darwin" else f"apt install {dep}",
            )

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("  Diagnosis Summary")
    print("=" * 50)
    if not diag.issues:
        print("  All checks passed! No issues found.")
    else:
        print(f"  Found {len(diag.issues)} issue(s):")
        for i, issue in enumerate(diag.issues, 1):
            print(f"  {i}. {issue}")

    if diag.issues and not auto_fix:
        print(f"\n  Run with --fix to attempt automatic repairs:")
        print(f"  python3 {os.path.abspath(__file__)} --fix")

    return diag.issues


if __name__ == "__main__":
    auto_fix = "--fix" in sys.argv
    issues = diagnose_all(auto_fix)
    sys.exit(len(issues))
