#!/usr/bin/env python3
"""Wrapper to run demo with UTF-8 encoding."""
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Now run the demo
exec(open('demo_complete_system.py', encoding='utf-8').read())
