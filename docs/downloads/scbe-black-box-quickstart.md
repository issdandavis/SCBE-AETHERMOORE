# SCBE Black Box Quickstart

SCBE Black Box explains why a Windows workstation, local AI job, or automation
run is likely to fail.

It is self-serve. No installation service is required.

## Prove It Locally

From the repo:

```powershell
npm run blackbox:prove
```

That command builds the buyer ZIP, runs the bundled scanner, and prints the top
finding plus the text/JSON report paths.

## Run

From the downloadable Black Box bundle:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-windows.ps1
```

From the repository or Workcell bundle:

```powershell
npm run blackbox:report
```

Or directly:

```powershell
python scripts/system/scbe_black_box.py
```

For CI or scheduled demos that should write a report without failing the job:

```powershell
python scripts/system/scbe_black_box.py --no-fail-on-high
```

## Output

The tool writes:

```text
artifacts/black_box/latest_black_box_report.json
artifacts/black_box/latest_black_box_report.txt
```

The text report is the human-facing value:

```text
[HIGH] Windows recorded an unexpected shutdown
Why: Event 41 means Windows restarted without a clean shutdown.
Do:  Correlate the minutes before this event with disk, driver, WHEA, BugCheck, and power events below.
Evidence: Microsoft-Windows-Kernel-Power #41...
```

## Signals Checked

- free disk space
- free memory
- recent Windows System critical/error/warning events
- unexpected shutdown events
- bugcheck/BSOD events
- disk/filesystem/storage warnings
- WHEA hardware warnings
- repeated Windows service crashes
- top memory processes

## Exit Codes

- `0`: no high-severity finding
- `1`: high-severity finding detected

Exit `1` is not a crash. It means the black box found something worth reading.
