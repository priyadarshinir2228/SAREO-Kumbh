# Phase 6: run every SNAP speckle filter configuration on the T1 radar-geometry subset, terrain-correct with the
# Phase 5 settings and crop to the AOI grid. Output: 03_enhanced\S1_filters\T1_<tag>_lin.tif (bands VH, VV; linear)
# Usage: powershell -File run_filters.ps1 [-Input <.dim>] [-Only <tag>]
param(
    [string]$InputDim = "D:\SAREO-Kumbh\03_enhanced\S1_filters\work\T1_cal_subset.dim",
    [string]$Only = ""
)
$root = "D:\SAREO-Kumbh"
. "$root\10_scripts\sareo_env.ps1" | Out-Null
$gpt = "D:\esa-snap\bin\gpt.exe"
$out = "$root\03_enhanced\S1_filters"
$work = "$out\work"

# tag, SNAP filter name, kernel size, Lee Sigma window
$configs = @(
    @('none', 'None', 3, '7x7'),
    @('boxcar3', 'Boxcar', 3, '7x7'), @('boxcar5', 'Boxcar', 5, '7x7'), @('boxcar7', 'Boxcar', 7, '7x7'),
    @('median3', 'Median', 3, '7x7'), @('median5', 'Median', 5, '7x7'), @('median7', 'Median', 7, '7x7'),
    @('lee3', 'Lee', 3, '7x7'), @('lee5', 'Lee', 5, '7x7'), @('lee7', 'Lee', 7, '7x7'),
    @('frost3', 'Frost', 3, '7x7'), @('frost5', 'Frost', 5, '7x7'), @('frost7', 'Frost', 7, '7x7'),
    @('gammamap3', 'Gamma Map', 3, '7x7'), @('gammamap5', 'Gamma Map', 5, '7x7'), @('gammamap7', 'Gamma Map', 7, '7x7'),
    @('refinedlee', 'Refined Lee', 3, '7x7'),
    @('leesigma7', 'Lee Sigma', 3, '7x7'), @('leesigma9', 'Lee Sigma', 3, '9x9'),
    @('idan', 'IDAN', 3, '7x7'),
    @('mulog', 'MuLoG', 3, '7x7')
)
$timing = @()
foreach ($c in $configs) {
    $tag, $filter, $size, $lsw = $c
    if ($Only -and $tag -ne $Only) { continue }
    $final = "$out\T1_${tag}_lin.tif"
    if (Test-Path $final) { Write-Host "skip $tag"; continue }
    $t0 = Get-Date
    & $gpt "$root\09_docs\snap_graphs\S1_filter_tc.xml" "-Pinput=$InputDim" "-Pfilter=$filter" "-Psize=$size" "-PlsWindow=$lsw" "-Penl=4.4" "-Plooks=4" `
        "-Poutput=$work\T1_${tag}_tc" -q 8 -c 4G 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -match 'ERROR|Exception' }
    if (Test-Path "$work\T1_${tag}_tc.tif") {
        & $env:SAREO_PY -I "$root\10_scripts\finalize_s1.py" "$work\T1_${tag}_tc.tif" $final | Out-Null
        Remove-Item "$work\T1_${tag}_tc.tif"
    }
    $sec = [math]::Round(((Get-Date) - $t0).TotalSeconds)
    $ok = Test-Path $final
    Write-Host ("{0,-11} {1,-12} {2,4} s  {3}" -f $tag, $filter, $sec, $(if ($ok) { 'ok' } else { 'FAILED' }))
    $timing += [pscustomobject]@{ tag = $tag; filter = $filter; size = $size; window = $lsw; seconds = $sec; ok = $ok }
}
$timing | Export-Csv "$out\snap_filter_timing.csv" -NoTypeInformation -Append
