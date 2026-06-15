# Submit Core.AXON to microsoft/winget-pkgs

PR-ready manifests live at:

```
winget/manifests/c/Core/AXON/1.0.0/
├── Core.AXON.installer.yaml
├── Core.AXON.version.yaml
└── Core.AXON.defaultLocale.yaml
```

## Before opening / updating the PR

1. Build the installer: `.\build.bat`
2. Upload `release\AXON_Setup_v1.0.0.exe` to https://runaxon.xyz/downloads/
3. Refresh hash in manifests:
   ```powershell
   python scripts/hash_setup.py --patch-manifest
   Copy-Item winget\Core.AXON.*.yaml winget\manifests\c\Core\AXON\1.0.0\
   ```
4. Validate locally:
   ```powershell
   winget validate --manifest winget\manifests\c\Core\AXON\1.0.0
   ```

## Fork & PR steps

1. Fork https://github.com/microsoft/winget-pkgs
2. Create branch: `core-axon-1.0.0` (or update existing PR branch)
3. Copy **only** the folder `manifests/c/Core/AXON/1.0.0/` into your fork
   - Path is **case-sensitive**: `Core` / `AXON` / `1.0.0`
   - Do **not** put YAML in repo root or under `winget/`
4. One PR = one version folder (three YAML files only)

## PR description template

```markdown
## Description
Add AXON — agentic AI terminal assistant for Windows (Inno Setup, per-user install).

## Checklist
- [x] Signed the Contributor License Agreement
- [ ] Linked to an issue (if applicable)

## Manifest Checklist
- [x] Checked that there aren't other open PRs for the same manifest update/change
- [x] This PR only modifies one (1) manifest
- [x] Validated manifest locally with `winget validate --manifest <path>`
- [ ] Tested manifest locally with `winget install --manifest <path>`
- [x] Manifest conforms to the 1.12 schema

Installer: https://runaxon.xyz/downloads/AXON_Setup_v1.0.0.exe
```

## After merge

Users install with:

```powershell
winget install Core.AXON
```

## Common validation failures (fixed in this repo)

| Issue | Fix |
|-------|-----|
| `Manifest-Validation-Error` | Use schema **1.12.0**, not 1.6.0 |
| Wrong folder | `manifests/c/Core/AXON/1.0.0/` |
| Missing `License` | Added to `defaultLocale` |
| `Scope: machine` | Changed to `user` (Inno `PrivilegesRequired=lowest`) |
| Bad `InstallerUrl` | Real HTTPS URL on runaxon.xyz, not GitHub placeholder |
| ARP mismatch | `PackageName: AXON`, `Publisher: AXON Core Team` |

## Re-run bot on existing PR

Comment on the PR:

```
@wingetbot run
```
