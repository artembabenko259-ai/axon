# AXON — Install Guide

## Windows (developer)

```powershell
git clone <your-repo-url>
cd CLI
pip install -r requirements.txt
copy .env.example .env
# Set OPENROUTER_API_KEY in .env or via web config

# From any project folder:
C:\path\to\CLI\axon.bat doctor
C:\path\to\CLI\axon.bat
```

Add the CLI folder to your user **PATH** to run `axon` from anywhere.

## Windows (installer — recommended for users)

1. Download `AXON_Setup_v1.0.0.exe` from the release page (coming soon).
2. Run the installer (adds `axon` to PATH).
3. Open a new terminal:

```powershell
axon doctor
axon
```

## API key

- Web UI: `axon web` → http://localhost:3000/config  
- Or edit `%APPDATA%\AXON\config.json`

## Winget

```powershell
winget install Core.AXON
```

## Verify

```powershell
axon doctor
axon -p "say hello" --json
```

## Data locations

| Item | Path |
|------|------|
| Config | `%APPDATA%\AXON\config.json` |
| Sessions | `%APPDATA%\AXON\sessions\` |
| Runtime policy | `%APPDATA%\AXON\runtime_policy.json` |
| Input history | `%USERPROFILE%\.axon_history` |

Bridge (web ↔ CLI) listens on `127.0.0.1:8765` only.
