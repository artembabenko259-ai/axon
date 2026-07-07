@echo off
set PATH=C:\Qt\6.11.1\mingw_64\bin;C:\Qt\Tools\mingw1310_64\bin;%PATH%
set QT_QML_IMPORT_PATH=C:\Qt\6.11.1\mingw_64\qml
echo Starting AXON Workstation...
start "" "workstation\build\axon-workstation.exe"
