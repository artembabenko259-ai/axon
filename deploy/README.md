# Deploy assets for runaxon.xyz

Private site files go here. **Do not commit** built HTML, `.exe`, or hosting credentials.

## On the server (hosting FTP)

Upload to web root:

- `index.html` (landing)
- `version.json` (copy from `version.json.example`, edit version/url)
- `downloads/AXON_Setup.exe` (optional, or link to GitHub Release)

## version.json

CLI checks `https://runaxon.xyz/version.json` for updates (`axon update`).

## Gitignored paths

See root `.gitignore`: `deploy/site/`, `deploy/downloads/`, `.wrangler/`, `.vercel/`
