"""Small reproducible Android debug build using official SDK tools, no Gradle download.

python android/build.py --sdk C:/dev/tools/android-mla --jdk C:/Users/issda/.jdks/jdk-24.0.2
"""

import argparse
from pathlib import Path
import os
import shutil
import subprocess
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--jdk", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "build")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    classes = out / "classes"
    classes.mkdir(exist_ok=True)
    assets = out / "assets" / "mla"
    assets.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "core.js", "app.js", "style.css"):
        shutil.copyfile(here.parent / "mla_web" / name, assets / name)
    shutil.copyfile(here.parent / "mla_profile.json", assets / "profile.json")
    tools = args.sdk / "build-tools" / "35.0.0"
    platform = args.sdk / "platforms" / "android-35" / "android.jar"
    env = dict(os.environ, JAVA_HOME=str(args.jdk), PATH=str(args.jdk / "bin") + os.pathsep + os.environ["PATH"])

    def run(*argv):
        subprocess.run([str(x) for x in argv], check=True, env=env)

    run(
        args.jdk / "bin" / "javac.exe",
        "--release",
        "8",
        "-encoding",
        "UTF-8",
        "-classpath",
        platform,
        "-d",
        classes,
        *here.glob("src/**/*.java"),
    )
    jar = out / "classes.jar"
    with zipfile.ZipFile(jar, "w") as z:
        for path in classes.rglob("*.class"):
            z.write(path, path.relative_to(classes).as_posix())
    run(
        args.jdk / "bin" / "java.exe",
        "-Xmx256m",
        "-cp",
        tools / "lib" / "d8.jar",
        "com.android.tools.r8.D8",
        "--lib",
        platform,
        "--min-api",
        "26",
        "--output",
        out,
        jar,
    )
    unsigned = out / "unsigned.apk"
    resources = out / "resources.zip"
    run(tools / "aapt2.exe", "compile", "--dir", here / "res", "-o", resources)
    run(
        tools / "aapt2.exe",
        "link",
        "-I",
        platform,
        "--manifest",
        here / "AndroidManifest.xml",
        "-A",
        out / "assets",
        "--version-code",
        "1",
        "--version-name",
        "0.1.0-mla",
        "-o",
        unsigned,
        resources,
    )
    with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as z:
        z.write(out / "classes.dex", "classes.dex")
    aligned = out / "aligned.apk"
    run(tools / "zipalign.exe", "-f", "4", unsigned, aligned)
    # Standard debug key only; this is not a Play Store signing identity.
    key = Path.home() / ".android" / "spiralword-debug.keystore"
    key.parent.mkdir(exist_ok=True)
    if not key.exists():
        run(
            args.jdk / "bin" / "keytool.exe",
            "-genkeypair",
            "-keystore",
            key,
            "-storepass",
            "android",
            "-keypass",
            "android",
            "-alias",
            "androiddebugkey",
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "10000",
            "-dname",
            "CN=Spiral Word Debug",
        )
    apk = out / "Spiral-Word-MLA-debug.apk"
    run(
        args.jdk / "bin" / "java.exe",
        "-Xmx128m",
        "-jar",
        tools / "lib" / "apksigner.jar",
        "sign",
        "--ks",
        key,
        "--ks-key-alias",
        "androiddebugkey",
        "--ks-pass",
        "pass:android",
        "--key-pass",
        "pass:android",
        "--out",
        apk,
        aligned,
    )
    run(args.jdk / "bin" / "java.exe", "-Xmx128m", "-jar", tools / "lib" / "apksigner.jar", "verify", "--verbose", apk)
    print(apk)


if __name__ == "__main__":
    main()
