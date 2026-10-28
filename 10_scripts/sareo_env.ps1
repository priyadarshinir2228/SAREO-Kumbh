# Dot-source this in PowerShell before running project scripts:  . D:\SAREO-Kumbh\10_scripts\sareo_env.ps1
$env:SAREO_PY = "D:\conda_envs\sareo\python.exe"
$env:GDAL_DATA = "D:\conda_envs\sareo\Library\share\gdal"
$env:PROJ_LIB = "D:\conda_envs\sareo\Library\share\proj"
$env:GDAL_DRIVER_PATH = "D:\conda_envs\sareo\Library\lib\gdalplugins"   # JPEG2000 (Sentinel-2) driver plugin
$env:PATH = "D:\conda_envs\sareo;D:\conda_envs\sareo\Library\bin;D:\conda_envs\sareo\Scripts;$env:PATH"
Write-Host "sareo env ready: $env:SAREO_PY (GDAL_DATA and PROJ_LIB set)"
