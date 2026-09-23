"""Exercise the actual frozen importer with and without a file/package collision.

The fixture uses a file named 'python', so the macOS failure is reproducible on
case-sensitive systems too. It builds a broken control and a repaired executable
using the installed PyInstaller version, then runs both outside the source tree.
"""

from pathlib import Path
import os
import subprocess
import sys
import tempfile


def main() -> None:
    hook = Path(__file__).resolve().with_name("pyinstaller_python_path.py")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix="scbe-frozen-namespace-") as directory:
        root = Path(directory)
        package = root / "python" / "scbe"
        package.mkdir(parents=True)
        (package.parent / "__init__.py").write_text("", encoding="utf-8")
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "probe.py").write_text("VALUE = 43\n", encoding="utf-8")
        (root / "main.py").write_text(
            "from python.scbe.probe import VALUE\nassert VALUE == 43\nprint('frozen-import-ok')\n",
            encoding="utf-8",
        )
        collision_hook = root / "make_collision.py"
        collision_hook.write_text(
            "import os, sys\n"
            "path = os.path.join(sys._MEIPASS, 'python')\n"
            "if not os.path.exists(path):\n"
            "    with open(path, 'xb') as stream:\n"
            "        stream.write(b'simulated shared-library name collision')\n"
            "assert os.path.isfile(path), 'fixture needs a file/package collision'\n",
            encoding="utf-8",
        )
        for fixed in (False, True):
            name = "fixed" if fixed else "control"
            command = [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--onefile",
                "--noupx",
                "--name",
                name,
                "--runtime-hook",
                str(collision_hook),
            ]
            if fixed:
                command += ["--runtime-hook", str(hook)]
            command.append("main.py")
            build = subprocess.run(
                command, cwd=root, env=env, capture_output=True, text=True, timeout=180
            )
            if build.returncode:
                raise RuntimeError(
                    f"{name} build failed:\n{build.stdout[-4000:]}\n{build.stderr[-4000:]}"
                )
            executable = root / "dist" / (name + (".exe" if os.name == "nt" else ""))
            result = subprocess.run(
                [str(executable)],
                cwd=root / "dist",
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if fixed:
                if result.returncode or result.stdout.strip() != "frozen-import-ok":
                    raise RuntimeError(
                        f"Repair failed: {result.returncode}\n{result.stdout}\n{result.stderr}"
                    )
            elif (
                result.returncode == 0
                or "No module named 'python.scbe'" not in result.stderr
            ):
                raise RuntimeError(
                    f"Control did not reproduce the failure:\n{result.stdout}\n{result.stderr}"
                )
            print(
                f"{name}: {'import succeeded' if fixed else 'expected missing-module failure reproduced'}",
                flush=True,
            )


if __name__ == "__main__":
    main()
