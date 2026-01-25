# SCBE CLI Setup Guide

Make the SCBE CLI available globally in your terminal like `@scbe` or just `scbe`.

## Quick Install

### Windows

1. **Add to PATH**:

   ```cmd
   setx PATH "%PATH%;C:\path\to\scbe-aethermoore-demo"
   ```

   Replace `C:\path\to\scbe-aethermoore-demo` with your actual path.

2. **Restart your terminal** and type:
   ```cmd
   scbe
   ```

### macOS / Linux

1. **Make executable**:

   ```bash
   chmod +x scbe
   ```

2. **Add to PATH** (choose one):

   **Option A: Symlink to /usr/local/bin**

   ```bash
   sudo ln -s $(pwd)/scbe /usr/local/bin/scbe
   ```

   **Option B: Add to ~/.bashrc or ~/.zshrc**

   ```bash
   echo 'export PATH="$PATH:/path/to/scbe-aethermoore-demo"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Test it**:
   ```bash
   scbe
   ```

## Usage

Once installed, you can activate SCBE from anywhere:

```bash
# Start the CLI
scbe

# Or use @ prefix (if your shell supports it)
@scbe
```

## First Time?

When you first run `scbe`, type:

```
scbe> tutorial
```

This will walk you through:

- What SCBE is
- How it works
- Quick start guide
- Security features
- Real-world use cases

## Available Commands

```
tutorial   - Interactive tutorial (START HERE!)
encrypt    - Encrypt a message
decrypt    - Decrypt a message
attack     - Run attack simulation
metrics    - Display system metrics
help       - Show all commands
exit       - Exit the CLI
```

## Example Session

```bash
$ scbe

╔═══════════════════════════════════════════════════════════╗
║           SCBE-AETHERMOORE v3.0.0                         ║
║     Hyperbolic Geometry-Based Security Framework          ║
╚═══════════════════════════════════════════════════════════╝

Type 'tutorial' to get started, or 'help' for commands

scbe> tutorial
🎓 SCBE-AETHERMOORE TUTORIAL
============================================================

What would you like to learn about?
  1. What is SCBE?
  2. How does it work?
  3. Quick start guide
  4. Security features
  5. Use cases
  0. Back to main menu

Select topic (0-5): 1

============================================================
WHAT IS SCBE-AETHERMOORE?
============================================================

SCBE (Spectral Context-Bound Encryption) is a next-generation security
framework that uses hyperbolic geometry and signal processing to protect
your data.

🔑 KEY CONCEPTS:

• Context-Aware Security
  Your data is encrypted based on WHO you are, WHAT you're doing, and
  WHERE you are. This creates a unique "security fingerprint" for each
  transaction.

• 14-Layer Defense
  Unlike traditional encryption (1-2 layers), SCBE uses 14 independent
  security layers that work together like a symphony orchestra.

...
```

## Troubleshooting

### Command not found

**Windows**: Make sure you restarted your terminal after adding to PATH.

**macOS/Linux**: Run `which scbe` to verify it's in your PATH.

### Permission denied

**macOS/Linux**: Run `chmod +x scbe` to make it executable.

### Python not found

Make sure Python 3.7+ is installed:

```bash
python --version
```

## Uninstall

### Windows

Remove the directory from your PATH environment variable.

### macOS / Linux

```bash
# If you used symlink
sudo rm /usr/local/bin/scbe

# If you modified .bashrc/.zshrc
# Remove the export PATH line from the file
```

## Need Help?

- Run `scbe` and type `tutorial` for an interactive guide
- Check the README.md for full documentation
- Visit the GitHub repo for issues and discussions
