#!/usr/bin/env node
/**
 * SCBE Visual System Launcher
 *
 * Starts both the visual interface (InkOS) and the SCBE security backend.
 * This is the single entry point for the entire system.
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');

console.log(`
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ███████╗ ██████╗██████╗ ███████╗    ██╗   ██╗██╗███████╗       ║
║   ██╔════╝██╔════╝██╔══██╗██╔════╝    ██║   ██║██║██╔════╝       ║
║   ███████╗██║     ██████╔╝█████╗      ██║   ██║██║███████╗       ║
║   ╚════██║██║     ██╔══██╗██╔══╝      ╚██╗ ██╔╝██║╚════██║       ║
║   ███████║╚██████╗██████╔╝███████╗     ╚████╔╝ ██║███████║       ║
║   ╚══════╝ ╚═════╝╚═════╝ ╚══════╝      ╚═══╝  ╚═╝╚══════╝       ║
║                                                                   ║
║   SCBE-AETHERMOORE Visual Operating System v1.0.0                ║
║   14-Layer Quantum-Resistant Security Framework                   ║
║   USPTO Patent #63/961,403                                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
`);

console.log('🚀 Starting SCBE Visual System...\n');

// Start the Python API backend
console.log('📡 Starting SCBE Security Backend (Port 8000)...');
const apiProcess = spawn('python', [join(rootDir, '..', 'src', 'api', 'main.py')], {
  cwd: join(rootDir, '..'),
  stdio: 'inherit',
  shell: true
});

apiProcess.on('error', (err) => {
  console.error('❌ Failed to start API backend:', err.message);
  console.log('   Make sure Python and FastAPI are installed.');
});

// Give the API a moment to start, then launch the UI
setTimeout(() => {
  console.log('\n🖥️  Starting InkOS Visual Interface (Port 5173)...');
  const uiProcess = spawn('npx', ['vite', '--host'], {
    cwd: rootDir,
    stdio: 'inherit',
    shell: true
  });

  uiProcess.on('error', (err) => {
    console.error('❌ Failed to start UI:', err.message);
  });

  console.log(`
┌─────────────────────────────────────────────────────────────────┐
│  System Ready!                                                  │
│                                                                 │
│  🖥️  Visual Interface: http://localhost:5173                    │
│  📡 Security API:      http://localhost:8000                    │
│  📚 API Docs:          http://localhost:8000/docs               │
│                                                                 │
│  Apps Available:                                                │
│  • Polly Pad    - Your personal AI workspace                    │
│  • Fleet        - AI agent fleet management                     │
│  • IDE          - Code editor with SCBE security                │
│  • Automator    - Workflow automation                           │
│  • Mail         - Secure communications                         │
│                                                                 │
│  Press Ctrl+C to stop all services                              │
└─────────────────────────────────────────────────────────────────┘
`);

}, 2000);

// Handle shutdown
process.on('SIGINT', () => {
  console.log('\n\n🛑 Shutting down SCBE Visual System...');
  apiProcess.kill();
  process.exit(0);
});
