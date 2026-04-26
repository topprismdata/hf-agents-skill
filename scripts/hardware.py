#!/usr/bin/env python3
"""hardware.py — Hardware detection + model recommendation for hf-agents.

Wraps `hf agents fit` commands to provide user-friendly output.
Can be called standalone or by Claude Code skill.

Usage:
    python3 hardware.py                    # Full hardware report + recommendations
    python3 hardware.py --json             # JSON output for programmatic use
    python3 hardware.py --recommend-only   # Just model recommendations
    python3 hardware.py --top 5            # Top 5 recommendations
"""

import argparse
import json
import platform
import subprocess
import sys
import os
from typing import Optional


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command and return CompletedProcess."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    except FileNotFoundError:
        # Return a CompletedProcess-like result for missing commands
        return subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr=f"Command not found: {cmd[0]}")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=-2, stdout="", stderr=f"Command timed out")


def get_system_info() -> dict:
    """Gather local system info without hf-agents."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "arch": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
    }

    # macOS: get chip and memory via system_profiler
    if platform.system() == "Darwin":
        result = run_cmd(["sysctl", "-n", "machdep.cpu.brand_string"])
        if result.returncode == 0:
            info["cpu"] = result.stdout.strip()

        result = run_cmd(["sysctl", "-n", "hw.memsize"])
        if result.returncode == 0:
            info["memory_bytes"] = int(result.stdout.strip())
            info["memory_gb"] = round(int(result.stdout.strip()) / (1024**3), 1)

        # Apple Silicon chip name
        result = run_cmd(["sysctl", "-n", "hw.optional.arm64"])
        if result.returncode == 0 and result.stdout.strip() == "1":
            # On Apple Silicon, check for GPU cores
            result3 = run_cmd(["system_profiler", "SPHardwareDataType"])
            if result3.returncode == 0:
                for line in result3.stdout.split("\n"):
                    line = line.strip()
                    if "Chip:" in line:
                        info["chip"] = line.split("Chip:")[-1].strip()
                    elif "Memory:" in line:
                        info["memory"] = line.split("Memory:")[-1].strip()
                    elif "Total Number of Cores:" in line:
                        info["gpu_cores"] = line.split(":")[-1].strip()

    # Linux: get memory info
    elif platform.system() == "Linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        mem_kb = int(line.split()[1])
                        info["memory_gb"] = round(mem_kb / (1024**2), 1)
                        break
        except (FileNotFoundError, ValueError):
            pass

        # Check for NVIDIA GPU
        result = run_cmd(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
        if result.returncode == 0 and result.stdout.strip():
            gpus = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    gpus.append({"name": parts[0], "vram": parts[1]})
            if gpus:
                info["gpus"] = gpus

    return info


def get_hf_fit_system() -> Optional[dict]:
    """Call `hf agents fit system` to get hardware info."""
    result = run_cmd(["hf", "extensions", "exec", "agents", "fit", "system", "--json"])
    if result.returncode != 0:
        # Try alternate command format
        result = run_cmd(["hf", "agents", "fit", "system", "--json"])
    if result.returncode == 0 and result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return None


def get_hf_recommendations(top: int = 10, use_case: str = "coding") -> Optional[list]:
    """Call `hf agents fit recommend` to get model recommendations."""
    result = run_cmd(
        ["hf", "extensions", "exec", "agents", "fit", "recommend",
         "--json", "-n", str(top), "--use-case", use_case],
        timeout=60
    )
    if result.returncode != 0:
        result = run_cmd(
            ["hf", "agents", "fit", "recommend",
             "--json", "-n", str(top), "--use-case", use_case],
            timeout=60
        )
    if result.returncode == 0 and result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return None


def format_size_gb(size_str: str) -> str:
    """Try to parse a size string to GB."""
    size_str = size_str.upper().strip()
    if "GB" in size_str:
        return size_str
    if "MB" in size_str:
        mb = float(size_str.replace("MB", "").strip())
        return f"{mb/1024:.1f}GB"
    return size_str


def print_system_report(sys_info: dict, hf_info: Optional[dict]):
    """Print a user-friendly system report."""
    print("=" * 50)
    print("  Hardware Report")
    print("=" * 50)

    if "chip" in sys_info:
        print(f"  Chip:    {sys_info['chip']}")
    elif "cpu" in sys_info:
        print(f"  CPU:     {sys_info['cpu']}")

    if "memory" in sys_info:
        print(f"  Memory:  {sys_info['memory']}")
    elif "memory_gb" in sys_info:
        print(f"  Memory:  {sys_info['memory_gb']} GB")

    if "gpu_cores" in sys_info:
        print(f"  GPU:     {sys_info['gpu_cores']} cores")

    if "gpus" in sys_info:
        for i, gpu in enumerate(sys_info["gpus"]):
            print(f"  GPU {i}:   {gpu['name']} ({gpu['vram']})")

    print(f"  OS:      {sys_info['os']} ({sys_info['arch']})")

    if hf_info:
        # Print any additional info from hf-agents
        for key in ["cuda", "metal", "vram", "recommended_quantization"]:
            if key in hf_info:
                print(f"  {key}: {hf_info[key]}")

    print()


def print_recommendations(recs: Optional[list], fallback=True):
    """Print model recommendations in a user-friendly table."""
    if recs:
        print("Recommended models (by fitness for your hardware):")
        print("-" * 70)
        for i, rec in enumerate(recs, 1):
            name = rec.get("model_id", rec.get("name", "Unknown"))
            quant = rec.get("quantization", rec.get("quant", ""))
            size = rec.get("size", rec.get("model_size", ""))
            speed = rec.get("speed", rec.get("tok_per_s", ""))
            score = rec.get("score", rec.get("fitness", ""))

            parts = [f"{i}. {name}"]
            if quant:
                parts.append(f"({quant})")
            if size:
                parts.append(f"- ~{format_size_gb(str(size))}")
            if speed:
                parts.append(f", ~{speed} tok/s")
            if score:
                parts.append(f"[fitness: {score}]")

            print("  " + " ".join(parts))
        print()

    elif fallback:
        # Provide sensible defaults based on system info
        print("Note: Could not fetch recommendations from hf-agents.")
        print("Here are some popular coding models for local use:")
        print("-" * 70)
        defaults = [
            ("Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "Q4_K_M", "~5GB", "Apple Silicon / 8GB+ GPU"),
            ("Qwen/Qwen2.5-Coder-14B-Instruct-GGUF", "Q4_K_M", "~10GB", "16GB+ RAM / GPU"),
            ("Qwen/Qwen2.5-Coder-32B-Instruct-GGUF", "Q4_K_M", "~20GB", "32GB+ RAM / GPU"),
            ("microsoft/Phi-4-mini-instruct-gguf", "Q5_K_M", "~3GB", "Any modern system"),
            ("bartowski/gemma-3-4b-it-GGUF", "Q4_K_M", "~3GB", "Lightweight, any system"),
            ("TheBloke/deepseek-coder-6.7B-instruct-GGUF", "Q4_K_M", "~4GB", "Good balance"),
        ]
        for i, (name, quant, size, note) in enumerate(defaults, 1):
            print(f"  {i}. {name} ({quant}) - {size} — {note}")
        print()
        print("To use these with llama-server:")
        print('  hf download <model_id> --include "*Q4_K_M*"')
        print("  llama-server -m <downloaded_file.gguf> --port 8080")


def main():
    parser = argparse.ArgumentParser(description="Hardware detection & model recommendation")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--recommend-only", action="store_true", help="Only show recommendations")
    parser.add_argument("--top", type=int, default=10, help="Number of recommendations (default: 10)")
    parser.add_argument("--use-case", default="coding", help="Use case filter (default: coding)")
    args = parser.parse_args()

    # Gather info
    sys_info = get_system_info()
    hf_info = get_hf_fit_system()
    recs = get_hf_recommendations(top=args.top, use_case=args.use_case)

    if args.json:
        output = {
            "system": sys_info,
            "hf_fit": hf_info,
            "recommendations": recs,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    # Human-readable output
    if not args.recommend_only:
        print_system_report(sys_info, hf_info)

    print_recommendations(recs, fallback=True)


if __name__ == "__main__":
    main()
