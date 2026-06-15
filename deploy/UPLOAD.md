# Upload runaxon.xyz

## CityHost: SSH/FTP need your IP whitelisted

In panel → **SSH** or **FTP** → add your home IP to allowed list, then SFTP works.
Until then use **Файловий менеджер** (works in browser, no IP whitelist).

## Quick upload (file manager)

1. Download/open `deploy/runaxon-site.zip` from this repo folder on your PC
2. Panel → **Файловий менеджер** → `runaxon.xyz` root
3. Upload zip → **Extract** in place (or upload files from `deploy/site/` one by one)
4. **SSL** — tab «Безпека» → Let's Encrypt for `runaxon.xyz`
5. Upload `AXON_Setup.exe` to `downloads/` after `build.bat`

## Auth API (PHP + SQLite)

CityHost supports PHP. Upload the `api/` folder and enable writable `api/data/`.

1. Copy `api/config.example.php` → `api/config.local.php`
2. Set a long random `secret` string in `config.local.php`
3. Ensure `api/data/` is writable by PHP (chmod 755/775)
4. Test:
   - https://runaxon.xyz/login.html
   - https://runaxon.xyz/api/auth/public-config.php
   - `axon login` from CLI

### Google Sign-In (бесплатно, как на скрине OpenRouter)

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → OAuth client ID → **Web application**
2. **Authorized JavaScript origins:** `https://runaxon.xyz`
3. Client ID → `api/config.local.php` → `google_client_id`
4. Залить: `login.html`, `assets/auth.*`, `api/auth/google.php`, `api/auth/public-config.php`

Платы за вход через Google нет. Хостинг CityHost — как обычно.

```
deploy/site/api/
├── config.example.php
├── config.local.php      ← create on server (not in git)
├── bootstrap.php
├── data/                 ← writable SQLite
└── auth/
    ├── device-start.php
    ├── device-poll.php
    ├── device-link.php
    ├── register.php
    ├── login.php
    └── me.php
```

## What to upload

Upload **everything** from `deploy/site/` to the hosting root (including `assets/` folder):

```
/var/www/.../runaxon.xyz/
├── index.html
├── login.html
├── versions.html
├── privacy.html
├── install.ps1
├── version.json
├── versions.json
├── assets/
│   ├── style.css
│   ├── main.js
│   ├── versions.css
│   ├── versions.js
│   ├── auth.css
│   ├── auth.js
│   └── favicon.svg
├── api/
│   ├── bootstrap.php
│   ├── config.example.php
│   ├── data/
│   └── auth/
└── downloads/
    ├── AXON_Setup.exe        ← latest (after build.bat)
    └── archive/              ← older installers (optional)
        └── AXON_Setup_v0.9.3.exe
```

## Steps (your panel)

1. **SSL** — tab «Безпека» → enable Let's Encrypt for `runaxon.xyz`
2. **Файловий менеджер** → open site root `runaxon.xyz`
3. Upload files from `deploy/site/` (drag & drop)
4. Build installer locally: `build.bat` → upload `dist/.../AXON_Setup.exe` to `downloads/`
5. Test:
   - https://runaxon.xyz/
   - https://runaxon.xyz/versions.html
   - https://runaxon.xyz/version.json
   - https://runaxon.xyz/versions.json
   - https://runaxon.xyz/install.ps1
   - https://runaxon.xyz/login.html

## PowerShell install test

```powershell
irm https://runaxon.xyz/install.ps1 | iex
```

## Update release

1. Bump `VERSION` in `ui/branding.py`
2. Edit `deploy/site/version.json` (latest version + download_url)
3. Add a row to `deploy/site/versions.json` (set previous `latest` to `false`)
4. Upload new exe to `downloads/`; move old exe to `downloads/archive/` if you keep history
5. Re-upload `version.json` and `versions.json`

## Do NOT upload

- FTP passwords, `.env`, private keys
- Full `zenith-web/` source (only static files from `deploy/site/`)

## GitHub link on landing

Edit `index.html` → set `id="gh-link"` href to your public repo URL when ready.
