@echo off
cd /d "%~dp0.."
python scripts\upload_site_ftp.py --provix
pause
