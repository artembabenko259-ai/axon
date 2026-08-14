"""Hardware specs and local model recommendations (Odysseus-style Cookbook check)."""

from __future__ import annotations

import shutil
import subprocess
import sys


def get_total_ram_gb() -> float:
    """Returns total system RAM in GB using zero-dependency OS commands."""
    try:
        if sys.platform == "win32":
            # Run wmic
            out = subprocess.check_output(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                text=True,
                creationflags=0x08000000
            )
            for line in out.splitlines():
                clean = line.strip()
                if clean and clean.isdigit():
                    return int(clean) / (1024 ** 3)
        elif sys.platform == "darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            clean = out.strip()
            if clean.isdigit():
                return int(clean) / (1024 ** 3)
        else:
            # Linux / Unix
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            return int(parts[1]) / (1024 ** 2)  # kB to GB
    except Exception:
        pass
    return 8.0  # Safe default fallback


def get_gpu_info() -> str | None:
    """Detects Nvidia/CUDA GPUs using nvidia-smi command."""
    try:
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            out = subprocess.check_output(
                [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                creationflags=0x08000000 if sys.platform == "win32" else 0
            )
            lines = out.strip().splitlines()
            if lines:
                return lines[0].strip()  # e.g. "NVIDIA GeForce RTX 3060, 12288"
    except Exception:
        pass
    return None


def get_local_model_recommendation() -> str:
    """Returns Odysseus-style local LLM compatibility recommendation based on system specs."""
    ram = get_total_ram_gb()
    gpu = get_gpu_info()
    
    parts = [f"Detected hardware: {ram:.1f} GB RAM"]
    if gpu:
        parts.append(f"GPU: {gpu}")
    else:
        parts.append("GPU: CPU-only / No Nvidia GPU detected")

    recommendations = []
    
    # Analyze memory and GPU resources
    if ram < 8.0:
        recommendations.append("Llama-3.2-1B-Instruct or Qwen2.5-1.5B (very low resources)")
    elif ram < 16.0:
        recommendations.append("Llama-3.2-3B-Instruct or Qwen2.5-3B")
    elif ram < 32.0:
        recommendations.append("Llama-3-8B-Instruct or DeepSeek-Coder-7B or Mistral-7B")
        if gpu:
            recommendations.append("Qwen2.5-7B (highly recommended for coding on GPU)")
    else:
        recommendations.append("DeepSeek-Coder-33B (advanced coding)")
        recommendations.append("Qwen2.5-14B-Instruct or Llama-3-8B")

    if gpu:
        vram_parts = gpu.split(",")
        if len(vram_parts) == 2 and vram_parts[1].strip().isdigit():
            vram_mb = int(vram_parts[1].strip())
            vram_gb = vram_mb / 1024
            parts.append(f"({vram_gb:.1f} GB VRAM)")
            if vram_gb >= 12.0:
                recommendations.insert(0, f"Qwen2.5-14B-Instruct (runs fast on your {vram_gb:.1f}GB GPU)")
            elif vram_gb >= 6.0:
                recommendations.insert(0, f"Llama-3-8B-Instruct (runs fast on your {vram_gb:.1f}GB GPU)")

    rec_list = "\n    - ".join(recommendations)
    return (
        f"{', '.join(parts)}\n"
        f"  💡 LOCAL LLM RECOMMENDATION:\n"
        f"    - {rec_list}"
    )
