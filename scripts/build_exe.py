#!/usr/bin/env python3
"""
Build a standalone axon.exe with PyInstaller for Inno Setup packaging.

Stages bundled .axon assets (skills, docs, locales), compiles cli.py to a
single executable, and prints the output path for installer.iss.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
BUNDLE_DIR = BUILD_DIR / "bundle-staging"
DIST_EXE_DIR = ROOT / "dist" / "exe"
SPEC_DIR = BUILD_DIR / "pyinstaller"
WORK_DIR = SPEC_DIR / "work"
ICON_PATH = ROOT / "assets" / "axon.ico"


def parse_version() -> str:
    branding = ROOT / "ui" / "branding.py"
    text = branding.read_text(encoding="utf-8")
    match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else "1.0.0"


def stage_bundle_assets() -> Path:
    """Prepare build/bundle-staging/.axon for PyInstaller and Inno Setup."""
    axon_dst = BUNDLE_DIR / ".axon"
    if axon_dst.exists():
        shutil.rmtree(axon_dst)
    axon_dst.mkdir(parents=True)

    for rel in ("skills", "docs"):
        src = ROOT / ".axon" / rel
        if src.is_dir():
            shutil.copytree(
                src,
                axon_dst / rel,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak"),
            )

    locales_dst = axon_dst / "locales"
    locales_dst.mkdir(parents=True, exist_ok=True)
    locales_src = ROOT / "zenith-web" / "locales"
    for path in sorted(locales_src.glob("*.json")):
        shutil.copy2(path, locales_dst / path.name)
    mastery_src = locales_src / "skills-mastery"
    if mastery_src.is_dir():
        mastery_dst = locales_dst / "skills-mastery"
        mastery_dst.mkdir(parents=True, exist_ok=True)
        for path in sorted(mastery_src.glob("*.json")):
            shutil.copy2(path, mastery_dst / path.name)

    return BUNDLE_DIR


def collect_add_data_args() -> list[str]:
    """Ship runtime data inside the PyInstaller folder.

    .axon skills/docs are NOT embedded — Inno Setup copies them to {app}\\.axon
  beside axon.exe. Embedding them in onefile caused PyInstaller extraction
  failures (PYI-15668) on some machines.
    """
    args: list[str] = []
    sep = ";" if sys.platform == "win32" else ":"

    env_example = ROOT / ".env.example"
    if env_example.is_file():
        args.extend(["--add-data", f"{env_example}{sep}."])

    return args


def collect_hidden_imports() -> list[str]:
    modules = [
        "agent_manager",
        "backup_manager",
        "bridge",
        "command_parser",
        "config_store",
        "llm_client",
        "skills_manager",
        "task_manager",
        "axon_runtime",
        "axon_bridges",
        "skills.tools",
        "skills.tasks",
        "skills.base",
        "session_store",
        "runtime_policy",
        "pricing",
        "approval_bridge",
        "audit_log",
        "mcp_client",
        "axon_doctor",
        "axon_auth",
        "zenith_server",
        "ui.repl",
        "ui.axon_tui",
        "ui.headless",
        "ui.axon_completer",
        "ui.branding",
        "ui.completer",
        "ui.file_context",
        "ui.git_commit",
        "ui.git_review",
        "ui.theme",
        "ui.config_cmd",
        "ui.provider_cmd",
        "ui.autopilot_cmd",
        "ui.skills_cmd",
        "ui.math_formatter",
        "code_mapper",
        "code_patcher",
        "code_search",
        "ui.side_by_side_diff",
        "git_transactions",
        "dependency_finder",
        "system_info",
        "prompt_toolkit",
        "rich",
        "rich.markdown",
        "colorama",
        "openai",
        "websockets",
        "ddgs",
        "pyfiglet",
        "pyfiglet.fonts",
        "dotenv",
        "google.genai",
        "google.genai.types",
        "pydantic",
    ]
    args: list[str] = []
    for module in modules:
        args.extend(["--hidden-import", module])
    return args


def collect_pyfiglet_data() -> list[str]:
    """Bundle full pyfiglet package (fonts subpackage + .flf files)."""
    import pyfiglet

    sep = ";" if sys.platform == "win32" else ":"
    fonts_init = Path(pyfiglet.__file__).resolve().parent / "fonts" / "__init__.py"
    args = [
        "--collect-all",
        "pyfiglet",
    ]
    if fonts_init.is_file():
        args.extend(["--add-data", f"{fonts_init}{sep}pyfiglet/fonts"])
    return args


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required. Install with: pip install pyinstaller"
        ) from exc


def collect_exclude_modules() -> list[str]:
    """Keep the frozen binary lean — exclude ML stacks not used by AXON."""
    excludes = [
        "torch",
        "torchaudio",
        "tensorflow",
        "sklearn",
        "scipy",
        "pandas",
        "matplotlib",
        "numba",
        "llvmlite",
        "gradio",
        "spacy",
        "nltk",
        "bitsandbytes",
        "sympy",
        "tkinter",
        "_tkinter",
    ]
    args: list[str] = []
    for module in excludes:
        args.extend(["--exclude-module", module])
    return args


def run_pyinstaller(*, clean: bool) -> Path:
    ensure_pyinstaller()
    import PyInstaller.__main__

    DIST_EXE_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(ROOT / "cli.py"),
        "--name=axon",
        "--onedir",
        "--console",
        f"--distpath={DIST_EXE_DIR}",
        f"--workpath={WORK_DIR}",
        f"--specpath={SPEC_DIR}",
        "--noconfirm",
    ]
    if clean:
        cmd.append("--clean")

    if ICON_PATH.is_file():
        cmd.extend(["--icon", str(ICON_PATH)])
    else:
        print("Warning: assets/axon.ico not found — run: python scripts/build_icon.py")

    cmd.extend(collect_add_data_args())
    cmd.extend(collect_hidden_imports())
    cmd.extend(collect_pyfiglet_data())
    cmd.extend(["--collect-all", "google", "--collect-all", "pydantic"])
    cmd.extend(collect_exclude_modules())
    cmd.append("--noupx")

    print("Running PyInstaller...")
    PyInstaller.__main__.run(cmd)

    print("Running PyInstaller for uar...")
    uar_cmd = [
        str(ROOT / "uar.py"),
        "--name=uar",
        "--onefile",
        "--console",
        f"--distpath={DIST_EXE_DIR / 'axon'}",
        f"--workpath={WORK_DIR}",
        f"--specpath={SPEC_DIR}",
        "--noconfirm",
    ]
    if clean:
        uar_cmd.append("--clean")
    uar_cmd.extend(collect_exclude_modules())
    uar_cmd.append("--noupx")
    PyInstaller.__main__.run(uar_cmd)

    binary_name = "axon.exe" if sys.platform == "win32" else "axon"
    uar_name = "uar.exe" if sys.platform == "win32" else "uar"
    
    exe_path = DIST_EXE_DIR / "axon" / binary_name
    uar_path = DIST_EXE_DIR / "axon" / uar_name
    
    if not exe_path.is_file():
        raise SystemExit(f"Build failed — {exe_path} was not created.")
    if not uar_path.is_file():
        raise SystemExit(f"Build failed — {uar_path} was not created.")
    return exe_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build standalone axon.exe")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Pass --clean to PyInstaller",
    )
    parser.add_argument(
        "--bundle-only",
        action="store_true",
        help="Only stage .axon assets (skip PyInstaller)",
    )
    args = parser.parse_args()

    version = parse_version()
    print(f"AXON build v{version}")
    print("Staging bundled .axon assets...")
    stage_bundle_assets()
    print(f"  -> {BUNDLE_DIR / '.axon'}")

    if args.bundle_only:
        return 0

    exe_path = run_pyinstaller(clean=args.clean)
    size_mb = exe_path.stat().st_size / (1024 * 1024)

    print()
    print("=" * 72)
    print("PyInstaller build complete")
    print("=" * 72)
    binary_name = "axon.exe" if sys.platform == "win32" else "axon"
    print(f"  {binary_name} : {exe_path}")
    print(f"  Size     : {size_mb:.1f} MB")
    print(f"  Bundle   : {BUNDLE_DIR / '.axon'}")
    print()
    if sys.platform == "win32":
        print("Next step — compile Inno Setup installer:")
        print('  iscc scripts\\installer.iss')
    else:
        print("Next step — run release packaging script or test local binary:")
        print('  ./dist/exe/axon/axon')
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
