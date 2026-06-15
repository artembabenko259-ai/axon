# AXON Windows Build Guide (PyInstaller + Inno Setup + Winget)

This guide produces a single professional Windows installer **`AXON_Setup_v1.0.0.exe`** that:

- Installs standalone **`axon.exe`** (no separate Python install required)
- Ships bundled **`.axon/`** skills, docs, and 3-language locales
- Adds the install folder to your **user PATH** (`axon` works in any terminal)
- Supports **silent install** flags for Winget (`/VERYSILENT`, `/SUPPRESSMSGBOXES`)

Package identity: **`Core.AXON`** · Publisher: **AXON Core Team**

---

## Prerequisites

| Tool | Purpose | Download |
|------|---------|----------|
| **Python 3.10+** | Build scripts | [python.org](https://www.python.org/downloads/) |
| **PyInstaller** | Compile `axon.exe` | `pip install -r requirements-build.txt` |
| **Inno Setup 6** | Create `AXON_Setup_v1.0.0.exe` | [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php) |
| **WinGet** (optional) | Validate / test manifests | Microsoft Store — *App Installer* |

Install Inno Setup with default options. The compiler **`iscc.exe`** is typically at:

```
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

Add that folder to PATH, or call it with the full path.

---

## One-click build (recommended)

Double-click or run from the repository root:

```powershell
.\build.bat
```

This automatically:

1. Creates/uses `.venv-build` with lean dependencies
2. Builds `dist/exe/axon.exe` via PyInstaller
3. Finds Inno Setup `ISCC.exe` and compiles `scripts/installer.iss`
4. Copies `AXON_Setup_v1.0.0.exe` to `release/`
5. Prints SHA-256 and patches `winget/Core.AXON.installer.yaml`

---

## Manual build (step by step)

From the repository root (use a **clean virtualenv** for smaller builds — see Troubleshooting):

```powershell
python -m venv .venv-build
.\.venv-build\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-build.txt
```

---

## Step 2 — Build `axon.exe` (PyInstaller)

```powershell
python scripts/build_exe.py --clean
```

**Outputs:**

| Path | Contents |
|------|----------|
| `dist/exe/axon.exe` | Single-file standalone executable |
| `build/bundle-staging/.axon/` | Skills, docs, EN/RU/UA locales for the installer |

Test the executable directly:

```powershell
.\dist\exe\axon.exe
```

---

## Step 3 — Compile the Inno Setup installer

```powershell
iscc scripts\installer.iss
```

Or with full path:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" scripts\installer.iss
```

**Output:** `dist/setup/AXON_Setup_v1.0.0.exe`

### Silent install (Winget-compatible)

```powershell
.\dist\setup\AXON_Setup_v1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
```

### What the installer does

1. Copies `axon.exe` to `%LOCALAPPDATA%\Programs\Core\AXON\` (or chosen directory)
2. Copies bundled `.axon\` templates beside the executable
3. Appends the install directory to **HKCU\Environment\Path** (user PATH)
4. Creates optional Start Menu / desktop shortcuts

Open a **new** terminal after install, then run:

```powershell
where axon
axon
```

---

## Step 4 — Hash the setup EXE for Winget

```powershell
python scripts/hash_setup.py --patch-manifest
```

This prints the SHA-256 and updates `winget/Core.AXON.installer.yaml`.

---

## Step 5 — Update Winget manifest URL

Edit `winget/Core.AXON.installer.yaml`:

```yaml
InstallerUrl: https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO/releases/download/v1.0.0/AXON_Setup_v1.0.0.exe
```

Upload `dist/setup/AXON_Setup_v1.0.0.exe` to that GitHub Release.

---

## Step 6 — Validate & test Winget locally

WinGet needs a **YAML-only** manifest folder:

```powershell
$mf = New-Item -ItemType Directory -Force -Path "$env:TEMP\core-axon-winget"
Copy-Item winget\Core.AXON.*.yaml $mf
winget validate --manifest $mf
winget install --manifest $mf
```

Uninstall test:

```powershell
winget uninstall Core.AXON
```

See also: `winget/TEST_GUIDE.md`

---

## Build pipeline (one-liner summary)

```powershell
python scripts/build_exe.py --clean
iscc scripts\installer.iss
python scripts/hash_setup.py --patch-manifest
```

---

## File map

```
scripts/
  build_exe.py      # PyInstaller → dist/exe/axon.exe
  installer.iss     # Inno Setup script
  hash_setup.py     # SHA-256 for Winget manifest
dist/
  exe/axon.exe
  setup/AXON_Setup_v1.0.0.exe
winget/
  Core.AXON.version.yaml
  Core.AXON.defaultLocale.yaml
  Core.AXON.installer.yaml
axon_runtime.py   # Frozen/install path helpers
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `PyInstaller is required` | `pip install -r requirements-build.txt` |
| `iscc` not recognized | Use full path to `ISCC.exe` (see above) |
| `axon` not found after install | Open a **new** terminal; PATH is user-scoped (HKCU) |
| `/docs` fails in installed build | Ensure `scripts/build_exe.py` bundled `docs_gen.py` (default) |
| Config not writable | Installed builds store `config.json` in `%APPDATA%\AXON\` |
| PyInstaller build is huge / slow | Use a fresh `.venv-build` with only `requirements.txt` + `requirements-build.txt` |

---

## Submitting to microsoft/winget-pkgs

1. Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)
2. Add manifests under `manifests/c/Core/AXON/1.0.0/`
3. Use the three files from `winget/` (rename to match repo conventions)
4. Open a PR with the setup EXE hosted on a stable HTTPS URL
