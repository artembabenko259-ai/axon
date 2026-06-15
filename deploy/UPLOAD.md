# Upload runaxon.xyz

## What to upload

Upload **everything** from `deploy/site/` to the hosting root:

```
/var/www/.../runaxon.xyz/
├── index.html
├── privacy.html
├── install.ps1
├── version.json
└── downloads/
    └── AXON_Setup.exe   ← you add this after build
```

## Steps (your panel)

1. **SSL** — tab «Безпека» → enable Let's Encrypt for `runaxon.xyz`
2. **Файловий менеджер** → open site root `runaxon.xyz`
3. Upload files from `deploy/site/` (drag & drop)
4. Build installer locally: `build.bat` → upload `dist/.../AXON_Setup.exe` to `downloads/`
5. Test:
   - https://runaxon.xyz/
   - https://runaxon.xyz/version.json
   - https://runaxon.xyz/install.ps1

## PowerShell install test

```powershell
irm https://runaxon.xyz/install.ps1 | iex
```

## Update release

1. Bump `VERSION` in `ui/branding.py`
2. Edit `deploy/site/version.json` (version + download_url)
3. Upload new exe to `downloads/`
4. Re-upload `version.json`

## Do NOT upload

- FTP passwords, `.env`, private keys
- Full `zenith-web/` source (only static files from `deploy/site/`)

## GitHub link on landing

Edit `index.html` → set `id="gh-link"` href to your public repo URL when ready.
