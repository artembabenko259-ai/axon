# Winget Local Test Guide — Core.AXON (Inno Setup)

Quick reference for validating and testing Winget manifests locally.

## PR-ready path

Files for [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs):

```
winget/manifests/c/Core/AXON/1.0.0/
```

Authoring copies (same content):

```
winget/Core.AXON.installer.yaml
winget/Core.AXON.version.yaml
winget/Core.AXON.defaultLocale.yaml
```

See **[SUBMIT.md](SUBMIT.md)** for the full PR checklist.

## Build first

```powershell
.\build.bat
python scripts\hash_setup.py --patch-manifest
```

## Validate manifests

```powershell
winget validate --manifest winget\manifests\c\Core\AXON\1.0.0
```

## Install via Winget (local manifest)

```powershell
winget install --manifest winget\manifests\c\Core\AXON\1.0.0
```

Winget downloads the installer from `InstallerUrl` and runs it silently with:

```
/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
```

## Verify

```powershell
where axon
axon doctor
```

## Uninstall

```powershell
winget uninstall Core.AXON
```

## Manifest identity

| Field | Value |
|-------|-------|
| PackageIdentifier | `Core.AXON` |
| PackageVersion | `1.0.0` |
| InstallerType | `inno` |
| Scope | `user` |
| Command | `axon` |
| Schema | `1.12.0` |
| InstallerUrl | `https://runaxon.xyz/downloads/AXON_Setup_v1.0.0.exe` |
