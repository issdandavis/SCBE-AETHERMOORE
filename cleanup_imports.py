import os
import glob
import re


def fix_imports():
    """Fix common relative import issues across all source files."""
    print(" Fixing import paths across source modules...")

    # Define search paths for .py files, excluding tests and virtual environments
    source_dirs = ['src']
    exclude_dirs = ['tests', '.venv', 'node_modules']
    files = []
    for directory in source_dirs:
        for root, dirs, filenames in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for filename in filenames:
                if filename.endswith(".py"):
                    files.append(os.path.join(root, filename))

    # Define common import patterns to fix
    patterns = {
        r"from symphonic_cipher": "from src.symphonic_cipher",
        r"from harmonic": "from src.harmonic",
        r"from scbe_aethermoore": "from src.scbe_aethermoore",
        r"import polly_pads_runtime": "from src.polly_pads_runtime import",
    }

    fixed_count = 0
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        for search, replace in patterns.items():
            content = re.sub(search, replace, content)

        if original_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            fixed_count += 1

    print(f"✅ Fixed imports in {fixed_count} files.")


if __name__ == "__main__":
    fix_imports()
