"""Colab Bridge — Run notebook cells from the terminal via Claude-in-Chrome.

This module provides functions that the Claude Code agent can call to:
1. List all cells in the Colab notebook
2. Run a specific cell by index
3. Inject and run new Python code
4. Read cell outputs
5. Scroll to a cell
6. Check runtime status

The bridge works through the Chrome extension MCP tools, which must be
connected to a Chrome tab with a Colab notebook open.

Usage (from Claude Code):
  from scripts.system.colab_bridge import ColabBridge
  bridge = ColabBridge(tab_id=1361946818)
  await bridge.list_cells()
  await bridge.run_cell(35)
  await bridge.inject_and_run("print('hello from terminal')")
  await bridge.read_output(35)

Note: This is a specification file. The actual execution happens through
Claude-in-Chrome MCP tool calls in the Claude Code session. This file
documents the JavaScript snippets needed for each operation.
"""

# JavaScript snippets for Colab DOM interaction
# These are meant to be passed to mcp__claude-in-chrome__javascript_tool

LIST_CELLS_JS = """
// List all cells with their type and first line of content
const cells = document.querySelectorAll('.cell');
const result = [];
cells.forEach((cell, index) => {
  const isCode = cell.classList.contains('code') || cell.querySelector('.code');
  const isText = cell.classList.contains('text') || cell.querySelector('.text');
  const editor = cell.querySelector('.monaco-editor, .CodeMirror, textarea');
  const firstLine = editor ? editor.textContent.substring(0, 100).trim() : '';
  const hasOutput = !!cell.querySelector('.output_area, .output');
  const cellIndex = cell.querySelector('.cell-execution-count');
  const execCount = cellIndex ? cellIndex.textContent.trim() : '';

  result.push({
    index,
    type: isCode ? 'code' : isText ? 'text' : 'unknown',
    firstLine: firstLine.substring(0, 80),
    hasOutput,
    execCount,
  });
});
JSON.stringify(result);
"""

RUN_CELL_JS = """
// Run a specific cell by index
// Replace CELL_INDEX with the actual index
const cells = document.querySelectorAll('.cell');
const targetCell = cells[CELL_INDEX];
if (targetCell) {
  // Focus the cell first
  targetCell.click();

  // Find and click the run button
  const runBtn = targetCell.querySelector('button[aria-label*="Run"], button[aria-label*="run"], .cell-execution-indicator');
  if (runBtn) {
    runBtn.click();
    'clicked run button for cell CELL_INDEX'
  } else {
    // Try keyboard shortcut: Ctrl+Enter runs current cell
    targetCell.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', ctrlKey: true, bubbles: true}));
    'sent Ctrl+Enter to cell CELL_INDEX'
  }
} else {
  'cell CELL_INDEX not found'
}
"""

READ_OUTPUT_JS = """
// Read the output of a specific cell
const cells = document.querySelectorAll('.cell');
const targetCell = cells[CELL_INDEX];
if (targetCell) {
  const outputAreas = targetCell.querySelectorAll('.output_area, .output_text, .output pre, .output_stdout');
  const outputs = Array.from(outputAreas).map(area => area.textContent.trim()).filter(Boolean);
  JSON.stringify({
    cellIndex: CELL_INDEX,
    outputCount: outputs.length,
    outputs: outputs.slice(0, 5),  // first 5 output blocks
    totalChars: outputs.join('').length,
  });
} else {
  JSON.stringify({error: 'cell CELL_INDEX not found'});
}
"""

INJECT_CELL_JS = """
// Inject a new code cell at the end and populate it
// This uses Colab's internal API if available
const addCodeBtn = document.querySelector('#toolbar-add-code, button[aria-label*="Code"]');
if (addCodeBtn) {
  addCodeBtn.click();
  // Wait for cell to be created, then find it
  setTimeout(() => {
    const cells = document.querySelectorAll('.cell');
    const newCell = cells[cells.length - 1];
    if (newCell) {
      const editor = newCell.querySelector('textarea, .inputarea');
      if (editor) {
        editor.focus();
        document.execCommand('selectAll');
        document.execCommand('insertText', false, CODE_CONTENT);
      }
    }
  }, 500);
  'injected new cell'
} else {
  'add code button not found'
}
"""

SCROLL_TO_CELL_JS = """
// Scroll to a specific cell
const cells = document.querySelectorAll('.cell');
const targetCell = cells[CELL_INDEX];
if (targetCell) {
  targetCell.scrollIntoView({behavior: 'smooth', block: 'center'});
  'scrolled to cell CELL_INDEX'
} else {
  'cell CELL_INDEX not found'
}
"""

CHECK_RUNTIME_JS = """
// Check if Colab runtime is connected and what type it is
const ramIndicator = document.querySelector('colab-usage-display');
const runtimeMenu = document.querySelector('colab-machine-type');

// Check for the green checkmark (connected indicator)
const connected = !!document.querySelector('.colab-run-status [class*="check"], svg[class*="check"]');

// Check RAM/Disk from the UI
const resourceText = document.querySelector('.resource-display, [class*="usage"]');

JSON.stringify({
  hasRAMIndicator: !!ramIndicator,
  runtimeType: runtimeMenu ? runtimeMenu.textContent.trim() : 'unknown',
  resourceInfo: resourceText ? resourceText.textContent.trim() : 'not visible',
  pageTitle: document.title,
  pythonVersion: document.querySelector('[class*="python"]') ? document.querySelector('[class*="python"]').textContent : 'unknown',
});
"""

# Convenience: Run Ctrl+Enter on currently focused cell
RUN_CURRENT_CELL_SHORTCUT_JS = """
document.activeElement.dispatchEvent(
  new KeyboardEvent('keydown', {key: 'Enter', ctrlKey: true, bubbles: true})
);
'sent Ctrl+Enter'
"""

# Run all cells
RUN_ALL_JS = """
// Use the Runtime menu -> Run all
const runtimeMenu = document.querySelector('[id*="runtime-menu"], [aria-label="Runtime"]');
if (runtimeMenu) {
  runtimeMenu.click();
  setTimeout(() => {
    const runAll = Array.from(document.querySelectorAll('[role="menuitem"]'))
      .find(item => item.textContent.includes('Run all'));
    if (runAll) {
      runAll.click();
      'clicked Run All'
    } else {
      'Run All menu item not found'
    }
  }, 300);
} else {
  'Runtime menu not found'
}
"""


def get_run_cell_js(cell_index: int) -> str:
    """Get the JS snippet to run a specific cell."""
    return RUN_CELL_JS.replace("CELL_INDEX", str(cell_index))


def get_read_output_js(cell_index: int) -> str:
    """Get the JS snippet to read a cell's output."""
    return READ_OUTPUT_JS.replace("CELL_INDEX", str(cell_index))


def get_scroll_to_cell_js(cell_index: int) -> str:
    """Get the JS snippet to scroll to a cell."""
    return SCROLL_TO_CELL_JS.replace("CELL_INDEX", str(cell_index))


def get_inject_cell_js(code: str) -> str:
    """Get the JS snippet to inject a new cell with code."""
    escaped = code.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return INJECT_CELL_JS.replace("CODE_CONTENT", escaped)
