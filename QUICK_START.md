# SCBE-AETHERMOORE Quick Start Guide

## 🚀 60-Second Quick Start

### Installation
```bash
cd C:\Users\issda\Downloads\SCBE_Production_Pack
```

### Launch the CLI
```bash
python scbe-cli.py
```

### Your First Encryption

1. **Start the tutorial**
   ```
   scbe> tutorial
   ```
   
2. **Learn the basics** (select option 1-5)
   - Option 1: What is SCBE?
   - Option 2: How does it work?
   - Option 3: Quick start guide
   - Option 4: Security features
   - Option 5: Use cases
   - Option 0: Back to main menu

3. **Encrypt a message**
   ```
   scbe> encrypt
   Enter message: Hello, World!
   Enter key: my-secret-key
   ```

4. **Decrypt the message**
   ```
   scbe> decrypt
   Enter ciphertext: [paste the ciphertext from step 3]
   Enter key: my-secret-key
   ```

5. **Test security**
   ```
   scbe> attack
   Select attack: 1
   ```

## 📖 Available Commands

| Command | Description |
|---------|-------------|
| `tutorial` | Interactive tutorial (START HERE!) |
| `encrypt` | Encrypt a message |
| `decrypt` | Decrypt a message |
| `attack` | Run attack simulation |
| `metrics` | Display system metrics |
| `help` | Show available commands |
| `exit` | Exit the CLI |

## 💡 Important Notes

### Tutorial Navigation
- When you type `tutorial`, you enter the tutorial menu
- Select topics by typing numbers **1-5** (inside the tutorial menu)
- Type **0** to return to the main menu
- After viewing a topic, you'll automatically return to the tutorial menu

### Common Mistakes
❌ **Wrong**: Typing `2` at the main `scbe>` prompt
```
scbe> 2
Unknown command: 2
```

✅ **Correct**: Type `tutorial` first, then select option 2
```
scbe> tutorial
Select topic (0-5): 2
```

### Exit Options
- Type `exit` at the main prompt
- Press `Ctrl+C` to interrupt
- Press `Ctrl+D` (Unix) or `Ctrl+Z` (Windows) for EOF

## 🎯 Example Session

```
scbe> tutorial
Select topic (0-5): 1
[reads "What is SCBE?"]
Press Enter to continue...

Select topic (0-5): 3
[reads "Quick Start Guide"]
Press Enter to continue...

Select topic (0-5): 0
[back to main menu]

scbe> encrypt
Enter message: Secret data
Enter key: my-key-2026
✓ Encrypted successfully in 0.42ms
Ciphertext: SGVsbG8gV29ybGQh...

scbe> metrics
📊 SYSTEM METRICS
Uptime................... 99.99%
Active Layers............ 14/14

scbe> exit
Goodbye! 👋
```

## 🔧 Troubleshooting

### "No such file or directory"
Make sure you're in the correct directory:
```bash
cd C:\Users\issda\Downloads\SCBE_Production_Pack
python scbe-cli.py
```

### "Unknown command"
- Commands must be typed at the `scbe>` prompt
- Tutorial options (1-5) only work inside the tutorial menu
- Type `help` to see all available commands

### EOF Errors
All EOF errors are now handled gracefully. If you see one, it means:
- You pressed Ctrl+D (Unix) or Ctrl+Z (Windows)
- Input was piped and reached end of file
- The CLI will exit cleanly

## 🚀 Next Steps

1. **Try the Agent**: `python scbe-agent.py`
   - AI coding assistant
   - Web search with SCBE encryption
   - Built-in code library
   - Security scanner

2. **Run the Demo**: `python demo-cli.py`
   - Automated demonstration
   - Shows all features in action

3. **Read the Docs**:
   - `CLI_README.md` - Full CLI documentation
   - `AGENT_README.md` - Agent documentation
   - `COMPLETE_SYSTEM.md` - System overview

## 📚 Learn More

- **Tutorial**: Type `tutorial` and explore all 5 topics
- **Security**: Type `attack` to see defense mechanisms
- **Metrics**: Type `metrics` to see real-time status
- **Help**: Type `help` anytime for command reference

---

**Ready to secure your data? Type `tutorial` to begin! 🔐**
