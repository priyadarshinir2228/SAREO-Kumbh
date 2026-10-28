# Phase 5: run the SNAP preprocessing graph on every finished Sentinel-1 GRD zip in 01_raw\S1,
# then crop each output to the exact AOI grid (finalize_s1.py).
# Usage:  powershell -File D:\SAREO-Kumbh\10_scripts\run_s1_preproc.ps1 [-Graph <xml>] [-Tag nofilter] [-Force]
param(
    [string]$Graph = "D:\SAREO-Kumbh\09_docs\snap_graphs\S1_preproc_nofilter.xml",
    [string]$Tag = "nofilter",
    [switch]$Force
)
$root = "D:\SAREO-Kumbh"
$gpt = "D:\esa-snap\bin\gpt.exe"
. "$root\10_scripts\sareo_env.ps1" | Out-Null   # PATH to the env's GDAL DLLs + GDAL_DATA/PROJ_LIB
$py = $env:SAREO_PY
$aoi = (Get-Content "$root\06_vectors\AOI_Kumbh_4326.wkt" -Raw).Trim()
$outDir = "$root\02_preproc\S1"
$tmpDir = "$outDir\_snap_tmp"
New-Item -ItemType Directory -Force $tmpDir | Out-Null

Get-ChildItem "$root\01_raw\S1" -Filter "S1*_IW_GRDH_*.zip" | ForEach-Object {
    $date = $_.Name.Substring(17, 8)           # yyyymmdd from the product name
    $sat = $_.Name.Substring(0, 3)
    $name = "${sat}_${date}_Sig0_${Tag}"
    if ((Test-Path "$outDir\${name}_dB.tif") -and -not $Force) { Write-Host "skip $date (exists)"; return }
    Write-Host "processing $date ..."
    $t0 = Get-Date
    & $gpt $Graph "-Pinput=$($_.FullName)" "-Paoi=$aoi" "-PoutLinear=$tmpDir\${name}_lin" "-PoutDb=$tmpDir\${name}_dB" -q 8 -c 4G 2>&1 |
        ForEach-Object { "$_" } | Where-Object { $_ -match 'ERROR|Exception|SEVERE' }
    if (-not (Test-Path "$tmpDir\${name}_dB.tif")) { Write-Host "  FAILED for $date - SNAP wrote no output"; return }
    foreach ($kind in 'lin', 'dB') { & $py -I "$root\10_scripts\finalize_s1.py" "$tmpDir\${name}_$kind.tif" "$outDir\${name}_$kind.tif" }
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    if (Test-Path "$outDir\${name}_dB.tif") {
        Remove-Item "$tmpDir\${name}_*.tif"
        Write-Host "  done in $mins min"
        Add-Content "$root\09_docs\processing_log.csv" ("P5-auto,{0},5,SNAP gpt + finalize_s1.py,S1 preprocessing ({1}),{2}; crop to AOI grid,{3},02_preproc/S1/{4}_lin.tif + _dB.tif,ok,{5} min" -f `
            (Get-Date -Format yyyy-MM-dd), $Tag, (Split-Path $Graph -Leaf), $_.Name, $name, $mins)
    } else {
        Write-Host "  FAILED for $date at the crop step"
    }
}
