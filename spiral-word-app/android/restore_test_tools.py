"""Restore only this task's archived emulator tools after reclaiming local disk.

Archives on S: were fetched from Google's SDK repository. No new download.
The AVD's writable data stays on S:. Does not alter training or an existing AVD.
"""

import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile

PACKAGES = [
    ("emulator-windows_x64-15917651.zip", "54fa750822ff462d57e04fc8e98e60f08df2bb61", "emulator"),
    ("x86_64-28_r04.zip", "d47a85c8f4e9fd57df97814ad8884eeb0f3a0ef0", "system-images/android-28/default/x86_64"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, default=Path("C:/dev/tools/android-mla"))
    parser.add_argument("--archives", type=Path, default=Path("S:/Projects/SpiralWord/android-downloads"))
    args = parser.parse_args()
    for name, expected, target in PACKAGES:
        path = args.archives / name
        h = hashlib.sha1()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                h.update(chunk)
        if h.hexdigest() != expected:
            raise SystemExit("Archive checksum mismatch: " + name)
        dest = (args.sdk / target).resolve()
        if dest.exists():
            print("Already present; not overwriting:", dest)
            continue
        with zipfile.ZipFile(path) as archive:
            required = sum(item.file_size for item in archive.infolist())
            if shutil.disk_usage(args.sdk).free - required < 2.5 * 1024**3:
                raise SystemExit("Keep at least 2.5 GiB free for training after extraction")
            for item in archive.infolist():
                parts = Path(item.filename).parts[1:]
                if not parts:
                    continue
                out = (dest / Path(*parts)).resolve()
                if not out.is_relative_to(dest):
                    raise SystemExit("Unsafe archive entry")
                if item.is_dir():
                    out.mkdir(parents=True, exist_ok=True)
                else:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source, out.open("wb") as sink:
                        shutil.copyfileobj(source, sink, 1024 * 1024)
        print("Restored", dest)


if __name__ == "__main__":
    main()
