"""Capture/import physical response traces for MAHSS topology authentication.

The validation harness expects CSV columns: seed, repeat, sample_index, value.
This helper can import WAV files into that format now, and can record from a
microphone/contact sensor when the optional ``sounddevice`` package is present.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import wave

import numpy as np

try:  # Optional dependency; importing this script should not require audio I/O.
    import sounddevice as sd  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - depends on local machine packages.
    sd = None


def normalize_trace(samples: np.ndarray) -> np.ndarray:
    values = np.asarray(samples, dtype=np.float64).reshape(-1)
    if values.size == 0:
        raise ValueError("trace has no samples")
    values = values - float(np.mean(values))
    peak = float(np.max(np.abs(values))) or 1.0
    return values / peak


def read_wav_mono(path: Path) -> tuple[int, np.ndarray]:
    """Read a PCM WAV file and return sample rate plus normalized mono trace."""

    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        sample_width = handle.getsampwidth()
        frames = handle.readframes(handle.getnframes())
    if sample_width == 1:
        dtype = np.uint8
        scale = 128.0
        offset = 128.0
    elif sample_width == 2:
        dtype = np.int16
        scale = float(np.iinfo(np.int16).max)
        offset = 0.0
    elif sample_width == 4:
        dtype = np.int32
        scale = float(np.iinfo(np.int32).max)
        offset = 0.0
    else:
        raise ValueError(f"unsupported WAV sample width: {sample_width}")
    data = (np.frombuffer(frames, dtype=dtype).astype(np.float64) - offset) / scale
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return sample_rate, normalize_trace(data)


def trim_trace(samples: np.ndarray, *, start_sample: int = 0, max_samples: int | None = None) -> np.ndarray:
    if start_sample < 0:
        raise ValueError("start_sample must be >= 0")
    trimmed = np.asarray(samples, dtype=np.float64)[start_sample:]
    if max_samples is not None:
        if max_samples < 16:
            raise ValueError("max_samples must be >= 16")
        trimmed = trimmed[:max_samples]
    if trimmed.size < 16:
        raise ValueError("trimmed trace must contain at least 16 samples")
    return trimmed


def append_trace_csv(
    output: Path,
    *,
    seed: str,
    repeat: int,
    samples: np.ndarray,
    sample_rate: int | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    exists = output.exists()
    with output.open("a", encoding="utf-8", newline="") as handle:
        fieldnames = ("seed", "repeat", "sample_index", "value", "sample_rate_hz")
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for sample_index, value in enumerate(samples):
            writer.writerow(
                {
                    "seed": seed,
                    "repeat": repeat,
                    "sample_index": sample_index,
                    "value": f"{float(value):.12g}",
                    "sample_rate_hz": sample_rate or "",
                }
            )


def import_wav_to_csv(
    wav_path: Path,
    output: Path,
    *,
    seed: str,
    repeat: int,
    start_sample: int = 0,
    max_samples: int | None = None,
) -> dict[str, object]:
    sample_rate, samples = read_wav_mono(wav_path)
    samples = trim_trace(samples, start_sample=start_sample, max_samples=max_samples)
    append_trace_csv(output, seed=seed, repeat=repeat, samples=samples, sample_rate=sample_rate)
    return {
        "wav_path": str(wav_path),
        "output": str(output),
        "seed": seed,
        "repeat": repeat,
        "sample_rate_hz": sample_rate,
        "sample_count": int(samples.size),
    }


def record_to_csv(
    output: Path,
    *,
    seed: str,
    repeat: int,
    seconds: float = 2.0,
    sample_rate: int = 44_100,
    device: int | str | None = None,
    max_samples: int | None = None,
) -> dict[str, object]:
    if sd is None:
        raise RuntimeError("live recording requires optional package: pip install sounddevice")
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    data = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="float64", device=device)
    sd.wait()
    samples = trim_trace(normalize_trace(data[:, 0]), max_samples=max_samples)
    append_trace_csv(output, seed=seed, repeat=repeat, samples=samples, sample_rate=sample_rate)
    return {
        "output": str(output),
        "seed": seed,
        "repeat": repeat,
        "sample_rate_hz": sample_rate,
        "sample_count": int(samples.size),
        "device": device,
    }


def list_devices() -> list[dict[str, object]]:
    if sd is None:
        raise RuntimeError("device listing requires optional package: pip install sounddevice")
    devices = sd.query_devices()
    return [
        {
            "index": idx,
            "name": str(device.get("name", "")),
            "max_input_channels": int(device.get("max_input_channels", 0)),
            "default_samplerate": float(device.get("default_samplerate", 0.0)),
        }
        for idx, device in enumerate(devices)
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    devices = sub.add_parser("devices", help="List recording devices if sounddevice is installed.")
    devices.set_defaults(func=_cmd_devices)

    import_cmd = sub.add_parser("import-wav", help="Append one WAV trace to the MAHSS measurement CSV.")
    import_cmd.add_argument("--wav", type=Path, required=True)
    import_cmd.add_argument("--output", type=Path, required=True)
    import_cmd.add_argument("--seed", required=True)
    import_cmd.add_argument("--repeat", type=int, required=True)
    import_cmd.add_argument("--start-sample", type=int, default=0)
    import_cmd.add_argument("--max-samples", type=int, default=None)
    import_cmd.set_defaults(func=_cmd_import_wav)

    record_cmd = sub.add_parser("record", help="Record one live tap trace into the MAHSS measurement CSV.")
    record_cmd.add_argument("--output", type=Path, required=True)
    record_cmd.add_argument("--seed", required=True)
    record_cmd.add_argument("--repeat", type=int, required=True)
    record_cmd.add_argument("--seconds", type=float, default=2.0)
    record_cmd.add_argument("--sample-rate", type=int, default=44_100)
    record_cmd.add_argument("--device", default=None)
    record_cmd.add_argument("--max-samples", type=int, default=None)
    record_cmd.set_defaults(func=_cmd_record)
    return parser


def _cmd_devices(_args: argparse.Namespace) -> int:
    for device in list_devices():
        print(
            f"{device['index']}: {device['name']} "
            f"inputs={device['max_input_channels']} rate={device['default_samplerate']}"
        )
    return 0


def _cmd_import_wav(args: argparse.Namespace) -> int:
    result = import_wav_to_csv(
        args.wav,
        args.output,
        seed=args.seed,
        repeat=args.repeat,
        start_sample=args.start_sample,
        max_samples=args.max_samples,
    )
    print(result)
    return 0


def _cmd_record(args: argparse.Namespace) -> int:
    result = record_to_csv(
        args.output,
        seed=args.seed,
        repeat=args.repeat,
        seconds=args.seconds,
        sample_rate=args.sample_rate,
        device=args.device,
        max_samples=args.max_samples,
    )
    print(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
