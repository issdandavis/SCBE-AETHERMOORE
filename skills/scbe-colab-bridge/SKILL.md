---
name: scbe-colab-bridge
description: Control Google Colab notebooks from Claude Code via Chrome extension. Execute cells, run terminal commands, read outputs, and manage GPU compute remotely.
user_invocable: true
---

# SCBE Colab Bridge

Execute code on Google Colab from the Claude Code terminal via the Chrome extension bridge.

## Prerequisites

1. Chrome is open with Claude-in-Chrome extension connected
2. A Colab notebook is open in a Chrome tab
3. The Colab runtime is connected (green checkmark visible)

## Capabilities

### Terminal Commands (PREFERRED — handles multi-line code)
1. Click into the Colab terminal panel (right sidebar)
2. Type any bash/python command
3. Press Enter
4. Read output via screenshot

```
# Simple command
python3 -c "import torch; print(torch.__version__)"

# Write a script file then run it (avoids indentation issues)
cat > /content/my_script.py << 'EOF'
import torch
# ... multi-line Python with proper indentation
EOF
python3 /content/my_script.py
```

### Cell Execution (single-line only)
1. Click `+ Code` button at (170, 84) in toolbar
2. Click into the new cell editor
3. Type single-line Python with semicolons (NO indentation)
4. Press Ctrl+Enter
5. Read output via JS: `document.querySelectorAll('.output_text')`

### Cell Search (viewport-limited)
Inject ColabBridge then search:
```javascript
window.ColabBridge.findCell('search text')  // only finds rendered cells
window.ColabBridge.readOutput(cellIndex)     // read cell output
window.ColabBridge.runtimeStatus()           // check runtime
```

### Full Notebook Index
Use local copy at `notebooks/spiralverse_protocol_training_generator.ipynb`
Cell index at `artifacts/colab_bridge/notebook_cell_index.json`

## Known Limitations

| Issue | Workaround |
|-------|-----------|
| Multi-line code in cells gets wrong indentation | Use terminal or write to .py file first |
| Cell search only finds viewport-rendered cells | Use local notebook index for full search |
| Focus can shift from terminal to notebook editor | Always click terminal panel before typing |
| Colab lazy-loads cells | Scroll to cell before reading via JS |
| No GPU on free tier by default | Use Runtime > Change runtime type > GPU |

## Proven Bridge Pattern

```
1. mcp__claude-in-chrome__tabs_context_mcp (get tab ID)
2. mcp__claude-in-chrome__navigate (open Colab URL)
3. mcp__claude-in-chrome__computer screenshot (verify state)
4. mcp__claude-in-chrome__computer left_click (click terminal)
5. mcp__claude-in-chrome__computer type (enter command)
6. mcp__claude-in-chrome__computer key Enter (execute)
7. mcp__claude-in-chrome__computer wait 5 (wait for output)
8. mcp__claude-in-chrome__computer screenshot (read result)
```

## Key Cells in Current Notebook

| Cell | Content |
|------|---------|
| 82 | H1-B: Raw Q/K/V weight FFT (BREAKTHROUGH) |
| 83 | Mirror Differential Telemetry |
| 84 | Thermodynamic Mirage Spectral Mapping |
| 17 | Spiralverse SDK patent validation |
| 18 | Harmonic Cryptography d^2 test |
| 10 | SCBE Agent System demo |

## Training Data Generation

Every Colab bridge interaction generates potential SFT data:
- Command sent -> output received = (instruction, response) pair
- Error encountered -> fix applied = (problem, solution) pair
- Cell executed -> result analyzed = (task, completion) pair

These can be exported to `training/sft_records/` for model training.
