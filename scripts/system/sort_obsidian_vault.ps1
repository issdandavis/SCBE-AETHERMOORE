# Sort and organize the Obsidian Realmforge vault
$vault = "C:\Users\issda\OneDrive\Dropbox\Izack Realmforge"

# 1. Create proper folders if they don't exist
$folders = @(
    "Story Files",
    "ChatGPT Exports",
    "Lore",
    "Research Papers"
)
foreach ($f in $folders) {
    $path = Join-Path $vault $f
    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "Created: $f"
    }
}

# 2. Move loose story/book TXT files to Story Files
$storyFiles = @(
    "AVALON_BOOK_OUTLINE_FULL 1.txt",
    "AVALON_BOOK_OUTLINE_FULL.txt",
    "Based on all the research and your.txt",
    "Book things.txt",
    "Izack_Master_Lore_Archive23.txt",
    "# Epic Fantasy Mastery Transforming.txt",
    "# Positioning The Avalon Codex for.txt",
    "exposition.txt"
)
foreach ($f in $storyFiles) {
    $src = Join-Path $vault $f
    if (Test-Path $src) {
        $dst = Join-Path $vault "Story Files" $f
        Move-Item $src $dst -Force
        Write-Host "Moved to Story Files: $f"
    }
}

# Move remaining book TXT files (including unicode-named ones)
Get-ChildItem $vault -Filter "*.txt" -File | Where-Object { $_.Name -match "BOOK|Spiral|Avalon" } | ForEach-Object {
    $dst = Join-Path $vault "Story Files" $_.Name
    Move-Item $_.FullName $dst -Force
    Write-Host "Moved to Story Files: $($_.Name)"
}

# 3. Move ChatGPT exports
Get-ChildItem $vault -Filter "ChatGPT Data Export*.html" -File | ForEach-Object {
    $dst = Join-Path $vault "ChatGPT Exports" $_.Name
    Move-Item $_.FullName $dst -Force
    Write-Host "Moved to ChatGPT Exports: $($_.Name)"
}

# 4. Move PDFs to appropriate folders
$researchPDFs = @(
    "500 page doc on theroy.pdf",
    "Thalorion_Ultimate_Campaign_Compendium.pdf"
)
foreach ($f in $researchPDFs) {
    $src = Join-Path $vault $f
    if (Test-Path $src) {
        $dst = Join-Path $vault "Research Papers" $f
        Move-Item $src $dst -Force
        Write-Host "Moved to Research Papers: $f"
    }
}

# Move everweave PDF
$ewPdf = Join-Path $vault "everweave-export.pdf"
if (Test-Path $ewPdf) {
    $dst = Join-Path $vault "Story Files" "everweave-export.pdf"
    Move-Item $ewPdf $dst -Force
    Write-Host "Moved to Story Files: everweave-export.pdf"
}

# 5. Move Story Files etc/* into Story Files (consolidate)
$storyEtc = Join-Path $vault "Story Files etc"
if (Test-Path $storyEtc) {
    Get-ChildItem $storyEtc -File | ForEach-Object {
        $dst = Join-Path $vault "Story Files" $_.Name
        Move-Item $_.FullName $dst -Force
        Write-Host "Consolidated from 'Story Files etc': $($_.Name)"
    }
    # Remove empty folder
    if ((Get-ChildItem $storyEtc).Count -eq 0) {
        Remove-Item $storyEtc -Force
        Write-Host "Removed empty: Story Files etc/"
    }
}

# 6. Move Untitled folder contents into ChatGPT Exports (they're ChatGPT data)
$untitled = Join-Path $vault "Untitled"
if (Test-Path $untitled) {
    Get-ChildItem $untitled -File | ForEach-Object {
        $dst = Join-Path $vault "ChatGPT Exports" $_.Name
        Move-Item $_.FullName $dst -Force
        Write-Host "Moved from Untitled/: $($_.Name)"
    }
    if ((Get-ChildItem $untitled).Count -eq 0) {
        Remove-Item $untitled -Force
        Write-Host "Removed empty: Untitled/"
    }
}

# Untitled 1 - conversation chronicle goes to Lore
$untitled1 = Join-Path $vault "Untitled 1"
if (Test-Path $untitled1) {
    Get-ChildItem $untitled1 -File | ForEach-Object {
        $dst = Join-Path $vault "Lore" $_.Name
        Move-Item $_.FullName $dst -Force
        Write-Host "Moved from Untitled 1/: $($_.Name)"
    }
    if ((Get-ChildItem $untitled1).Count -eq 0) {
        Remove-Item $untitled1 -Force
        Write-Host "Removed empty: Untitled 1/"
    }
}

# Untitled 2 - empty
$untitled2 = Join-Path $vault "Untitled 2"
if (Test-Path $untitled2) {
    if ((Get-ChildItem $untitled2).Count -eq 0) {
        Remove-Item $untitled2 -Force
        Write-Host "Removed empty: Untitled 2/"
    }
}

# 7. Move avalon files into Story Files
$avalonFiles = Join-Path $vault "avalon files"
if (Test-Path $avalonFiles) {
    Get-ChildItem $avalonFiles -File | ForEach-Object {
        $dst = Join-Path $vault "Story Files" $_.Name
        Move-Item $_.FullName $dst -Force
        Write-Host "Consolidated from 'avalon files': $($_.Name)"
    }
    if ((Get-ChildItem $avalonFiles).Count -eq 0) {
        Remove-Item $avalonFiles -Force
        Write-Host "Removed empty: avalon files/"
    }
}

# 8. Move the VHDX (huge file, shouldn't be in vault)
$vhdx = Join-Path $vault "REalmForge.vhdx"
if (Test-Path $vhdx) {
    Write-Host "WARNING: Found REalmForge.vhdx in vault root. This is a large virtual disk file."
    Write-Host "  Size: $([math]::Round((Get-Item $vhdx).Length / 1GB, 2)) GB"
    Write-Host "  Consider moving this out of the Obsidian vault manually."
}

# 9. Move loose AWS md
$awsMd = Join-Path $vault "AWS labda Pass.md"
if (Test-Path $awsMd) {
    $dst = Join-Path $vault "SCBE Architecture" "AWS Lambda Pass.md"
    Move-Item $awsMd $dst -Force
    Write-Host "Moved: AWS labda Pass.md -> SCBE Architecture/AWS Lambda Pass.md"
}

# 10. Final listing
Write-Host "`n=== FINAL VAULT STRUCTURE ==="
Get-ChildItem $vault -Directory | ForEach-Object { Write-Host "  📁 $($_.Name)" }
Get-ChildItem $vault -File | ForEach-Object { Write-Host "  📄 $($_.Name)" }
