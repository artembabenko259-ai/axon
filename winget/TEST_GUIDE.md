# Winget Local Test Guide — Core.AXON (Inno Setup)

Quick reference for testing the **Inno Setup** installer and Winget manifests locally.

> The `winget/` folder must contain **only** the three `Core.AXON.*.yaml` files when running `winget validate` or `winget install --manifest`. Move this guide aside or copy YAML to a temp folder.

## Build first

Run the one-click builder from the repo root:

```powershell
.\build.bat
```

Or see **[BUILD_GUIDE.md](../BUILD_GUIDE.md)** for manual steps.

## Validate manifests

```powershell
$mf = New-Item -ItemType Directory -Force -Path "$env:TEMP\core-axon-winget"
Copy-Item winget\Core.AXON.*.yaml $mf
winget validate --manifest $mf
```

## Install via Winget (local manifest)

```powershell
$mf = New-Item -ItemType Directory -Force -Path "$env:TEMP\core-axon-winget"
Copy-Item winget\Core.AXON.*.yaml $mf
winget install --manifest $mf
```

Winget downloads `AXON_Setup_v1.0.0.exe` from `InstallerUrl` and runs it silently with:

```
/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
```

## Verify

```powershell
where axon
axon
```

## Uninstall

```powershell
winget uninstall Core.AXON
```

## Manifest identity

| Field | Value |
|-------|-------|
| PackageIdentifier | `Core.AXON` |
| InstallerType | `inno` |
| Command | `axon` |
| Schema | `1.6.0` |
