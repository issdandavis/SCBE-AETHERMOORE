from __future__ import annotations

from scripts.system.scbe_black_box import analyze


def test_black_box_flags_disk_pressure() -> None:
    findings = analyze(
        {
            "disks": [{"path": "C:\\", "free_gb": 3.2, "free_percent": 2.5}],
            "memory": {"free_gb": 12.0, "free_percent": 30.0},
            "windows_events": {"events": []},
        }
    )
    assert any(f.code == "disk_almost_full" and f.severity == "high" for f in findings)


def test_black_box_explains_unexpected_shutdown_and_storage_warning() -> None:
    findings = analyze(
        {
            "disks": [{"path": "C:\\", "free_gb": 100.0, "free_percent": 40.0}],
            "memory": {"free_gb": 8.0, "free_percent": 25.0},
            "windows_events": {
                "events": [
                    {
                        "time": "2026-06-16T03:14:00Z",
                        "id": 41,
                        "provider": "Microsoft-Windows-Kernel-Power",
                        "message": "The system has rebooted without cleanly shutting down first.",
                    },
                    {
                        "time": "2026-06-16T03:13:00Z",
                        "id": 153,
                        "provider": "Disk",
                        "message": "The IO operation at logical block address was retried.",
                    },
                ]
            },
        }
    )
    codes = {f.code for f in findings}
    assert "unexpected_shutdown" in codes
    assert "storage_warning" in codes


def test_black_box_low_when_no_signals() -> None:
    findings = analyze(
        {
            "disks": [{"path": "C:\\", "free_gb": 100.0, "free_percent": 40.0}],
            "memory": {"free_gb": 8.0, "free_percent": 25.0},
            "windows_events": {"events": []},
        }
    )
    assert [f.code for f in findings] == ["no_immediate_failure_signal"]
