$dirs = Get-ChildItem 'C:\Users\issda' -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notin @('AppData','Application Data','Local Settings','Cookies','Recent','Start Menu','My Documents','Links','Searches','Saved Games','Contacts','Favorites','3D Objects','IntelGraphicsProfiles','CrossDevice','ansel','SendTo','NetHood','PrintHood','Templates') }

$results = @()
foreach ($d in $dirs) {
    try {
        $size = (Get-ChildItem $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        if ($size -gt 1MB) {
            $results += [PSCustomObject]@{
                MB = [math]::Round($size / 1MB)
                Directory = $d.Name
            }
        }
    } catch {}
}
$results | Sort-Object MB -Descending | Select-Object -First 30 | Format-Table -AutoSize

Write-Host "`n--- AppData/Local top dirs ---"
$localDirs = Get-ChildItem 'C:\Users\issda\AppData\Local' -Directory -Force -ErrorAction SilentlyContinue
$localResults = @()
foreach ($d in $localDirs) {
    try {
        $size = (Get-ChildItem $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        if ($size -gt 50MB) {
            $localResults += [PSCustomObject]@{
                MB = [math]::Round($size / 1MB)
                Directory = $d.Name
            }
        }
    } catch {}
}
$localResults | Sort-Object MB -Descending | Select-Object -First 15 | Format-Table -AutoSize
