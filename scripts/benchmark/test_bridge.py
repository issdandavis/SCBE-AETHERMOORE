#!/usr/bin/env python3
"""Quick test of the PowerShell Ollama bridge via ask_ollama."""
import sys, importlib
sys.path.insert(0, '/mnt/c/Users/issda/SCBE-AETHERMOORE')

# Force fresh import (no cached pyc)
if 'scripts.benchmark.terminal_bench_scbe_agent' in sys.modules:
    del sys.modules['scripts.benchmark.terminal_bench_scbe_agent']

import scripts.benchmark.terminal_bench_scbe_agent as m
importlib.reload(m)

print("ask_ollama source:", m.__file__)

try:
    resp = m.ask_ollama(
        'Output only JSON, no prose: {"commands":["echo hi"],"done":true,"rationale":"ok"}',
        'qwen2.5:0.5b',
        'http://127.0.0.1:11434'
    )
    print('RESP:', repr(resp[:300]))
except Exception as e:
    import traceback
    traceback.print_exc()
