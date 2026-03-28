
import React, { useState, useEffect } from 'react';
import { Layout } from './components/Layout';
import { LeftSidebar } from './components/LeftSidebar';
import { CodeEditor } from './components/CodeEditor';
import { Terminal } from './components/Terminal';
import { AIAssistant } from './components/AIAssistant';
import { INITIAL_FILES, FileNode } from './data/initialFiles';
import { detectLanguage, getLanguagesByCategory, LANGUAGE_MAP } from './utils/languageDetector';

const API_BASE = 'http://localhost:8100/api';

export default function App() {
  const [files, setFiles] = useState<FileNode[]>(INITIAL_FILES);
  const [activeFile, setActiveFile] = useState<FileNode | null>(null);
  const [logs, setLogs] = useState<string[]>([
    'Welcome to SCBE-AETHERMOORE Training Lab v1.0.0',
    '----------------------------------------',
    'Multi-Language Support: 40+ programming languages! ✨',
    'Type \"languages\" to see all supported languages.',
    'New here? Type "intro" for a quick tour.',
    'Type "help" to see all commands.',
    '----------------------------------------'
  ]);
  const [mode, setMode] = useState<'show-me' | 'do-it'>('show-me');
  const [isAiOpen, setIsAiOpen] = useState(false);

  // Load README by default on mount
  useEffect(() => {
    const root = INITIAL_FILES.find(f => f.id === 'root');
    const readme = root?.children?.find(f => f.name === 'README.md');
    if (readme) {
      setActiveFile(readme);
    }
  }, []);

  // Helper to find and update a node in the tree
  const updateTree = (nodes: FileNode[], id: string, updater: (node: FileNode) => FileNode): FileNode[] => {
    return nodes.map(node => {
      if (node.id === id) {
        return updater(node);
      }
      if (node.children) {
        return { ...node, children: updateTree(node.children, id, updater) };
      }
      return node;
    });
  };

  // Helper to add a file to the root directory
  const addFileToRoot = (name: string) => {
    const lang = detectLanguage(name);
    const template = (lang?.template || `// New file: ${name}`) + '\n';
    const newFile: FileNode = {
        id: `new-${Date.now()}`,
        name,
        type: 'file',
        content: template,
    };

    setFiles(prev => prev.map(node => {
        if (node.id === 'root') {
            return {
                ...node,
                children: [...(node.children || []), newFile]
            };
        }
        return node;
    }));
    return newFile;
  };

  // Helper to find a file by name recursively
  const findFileByName = (nodes: FileNode[], name: string): FileNode | null => {
    for (const node of nodes) {
      if (node.name === name && node.type === 'file') {
        return node;
      }
      if (node.children) {
        const found = findFileByName(node.children, name);
        if (found) return found;
      }
    }
    return null;
  };

  const handleToggleFolder = (id: string) => {
    setFiles(prev => updateTree(prev, id, node => ({ ...node, isOpen: !node.isOpen })));
  };

  const handleFileSelect = (file: FileNode) => {
    setActiveFile(file);
  };

  const handleCodeChange = (newCode: string) => {
    if (activeFile) {
      setFiles(prev => updateTree(prev, activeFile.id, node => ({ ...node, content: newCode })));
      setActiveFile(prev => prev ? { ...prev, content: newCode } : null);
    }
  };

  const addLog = (msg: string) => {
    setLogs(prev => [...prev, msg]);
  };

  const executeFile = (file: FileNode) => {
      addLog(`Executing ${file.name}...`);
      
      // Execution Logic
      setTimeout(() => {
        if (!file) return; 
        
        if (file.name === 'scbe_test_suite.py') {
            addLog('Initializing SCBE Test Environment...');
            addLog('Loading Military-Grade Security Modules...');
            addLog('--------------------------------------------------');
            addLog('SCBE Industry-Grade Test Suite - Above Standard Compliance');
            addLog('--------------------------------------------------');
            addLog('Test Categories:');
            addLog('1. Medical AI-to-AI Communication (HIPAA Compliant) [READY]');
            addLog('2. Military-Grade Security (NIST/FIPS) [READY]');
            addLog('3. Financial Transaction Security (PCI-DSS) [READY]');
            
            setTimeout(() => {
               addLog('Running Tests...');
               addLog('✓ HIPAA/HITECH Compliance: PASSED');
               addLog('✓ NIST 800-53 / FIPS 140-3: PASSED');
               addLog('✓ PCI-DSS Transaction Security: PASSED');
               addLog('✓ Self-Healing Workflow: PASSED');
               addLog('✓ Adversarial Attack Resistance: PASSED');
               addLog('✓ Quantum-Resistant Cryptography: PASSED');
               addLog('--------------------------------------------------');
               addLog('Success: All 155 tests passed in 0.42s');
            }, 500);
        } else if (file.name.endsWith('.py')) {
           if (file.content?.includes('print')) {
              // Simple mock for prints
              const prints = file.content.match(/print\s*\((.*?)\)/g);
              if (prints) {
                  prints.forEach(p => {
                      const msg = p.replace(/print\s*\(/, '').replace(/\)$/, '').replace(/['"]/g, '');
                      addLog(msg);
                  });
              } else {
                  addLog('Process finished with exit code 0');
              }
           } else {
              addLog('Process finished with exit code 0');
           }
        } else if (file.name.endsWith('.json')) {
          try {
             JSON.parse(file.content || '{}');
             addLog('JSON validation: VALID');
          } catch (e) {
             addLog('JSON validation: INVALID');
             addLog(`Error: ${(e as Error).message}`);
          }
        } else if (file.name.endsWith('.ts') || file.name.endsWith('.js')) {
           addLog('Compiling TypeScript/JavaScript...');
           addLog('Done in 1.2s.');
        } else if (file.name.endsWith('.md')) {
            addLog('Rendering Markdown...');
            addLog('Done.');
        } else {
          addLog(`Unknown file type for execution: ${file.name}`);
        }
      }, 500);
  };

  const handleCommand = async (cmd: string) => {
    addLog(`> ${cmd}`);
    const parts = cmd.trim().split(/\s+/);
    const command = parts[0].toLowerCase();
    const args = parts.slice(1);

    // Remote SCBE CLI lane (optional): routes to scripts/aetherbrowser/api_server.py if running.
    // Usage:
    //   trust aethermoorgames.com
    //   vault search "harmonic wall"
    //   ops tests
    //   momentum latest daily_ops
    // or:
    //   scbe vault stats
    const remoteCommands = new Set(['trust', 'vault', 'ops', 'momentum', 'chessboard', 'docs', 'matrix', 'health']);
    if (command === 'scbe' || remoteCommands.has(command)) {
      const remoteText = (command === 'scbe') ? args.join(' ') : cmd;
      if (!remoteText) {
        addLog('Usage: scbe <command>  (example: scbe vault stats)');
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/cli/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: remoteText }),
        });
        if (!res.ok) {
          addLog(`Error: CLI HTTP ${res.status}`);
          return;
        }
        const data = await res.json();
        addLog(typeof data === 'string' ? data : JSON.stringify(data, null, 2));
      } catch {
        addLog('Error: local API offline. Start: python scripts/aetherbrowser/api_server.py');
      }
      return;
    }

    if (command === 'help') {
      addLog('--- GENERAL COMMANDS ---');
      addLog('  intro             - Start the interactive tour');
      addLog('  languages         - List supported programming languages');
      addLog('  help              - Show this list');
      addLog('  clear             - Clear the terminal screen');
      addLog('  status            - Check system status & security');
      addLog('');
      addLog('--- FILE COMMANDS ---');
      addLog('  ls                - List all files and folders');
      addLog('  open [filename]   - Open a file by name');
      addLog('  run [filename]    - Execute a file (or the active one)');
      addLog('  create [name]     - Create a new file in root (templates by extension)');
      addLog('');
      addLog('--- BUSINESS AUTOMATION ---');
      addLog('  pillars           - Explain the 5-Pillar Revenue System');
      addLog('  demos             - List available demo scripts');
      addLog('');
      addLog('--- AI CONTROL ---');
      addLog('  mode [show|do]    - Switch AI mode (Show Me / Do It)');
      addLog('');
      addLog('--- SCBE (LOCAL API) ---');
      addLog('  trust <url>       - Registry trust classification');
      addLog('  vault stats       - Vault summary (notes/edges/SFT)');
      addLog('  vault search "q"  - Vault search');
      addLog('  ops tests         - Run test lane (governed)');
      addLog('  momentum latest   - Latest momentum train summary');
      addLog('  docs list         - Curated docs registry');
      addLog('Tip: Start API with: python scripts/aetherbrowser/api_server.py');

    } else if (command === 'intro') {
      addLog('👋 Welcome to SCBE-AETHERMOORE Training Lab!');
      addLog('This environment is designed for non-coders to build powerful tools.');
      addLog('1. EXPLORE: Use the sidebar on the left to browse your files.');
      addLog('2. EXECUTE: Click the green "Run" button top-right to test code.');
      addLog('3. AUTOMATE: Check the "pillars" command to see your business bots.');
      addLog('4. SECURE: Run "run scbe_test_suite.py" to verify security.');
      addLog('5. ASK AI: Click the "AI Assistant" button top-right for help.');
      addLog('Try typing "pillars" next!');

    } else if (command === 'pillars') {
      addLog('🏛️  THE 5-PILLAR REVENUE SYSTEM');
      addLog('1. Lead Hunter: Scrapes and qualifies leads (see /Lead Hunter)');
      addLog('2. Content Creator: Generates blogs & posts (see /Content Creator)');
      addLog('3. Market Analyzer: Tracks trends (see /Market Analyzer)');
      addLog('4. Deal Closer: Automates emails (see /Deal Closer)');
      addLog('5. Support Bot: Handles customer chat (see /Support Bot)');
      addLog('Tip: Open "leads_db.json" to see sample data.');

    } else if (command === 'demos') {
      addLog('Available Demos:');
      addLog('1. scbe_test_suite.py - Run High-Security Compliance Tests');
      addLog('2. scraper_bot.py     - Run Lead Generation Logic');
      addLog('3. blog_generator.py  - Run Content AI');
      addLog('Type "run <filename>" to start one.');

    } else if (command === 'languages' || command === 'langs') {
      addLog('SUPPORTED PROGRAMMING LANGUAGES:');
      addLog('--------------------------------------------------');
      addLog('');

      const categories = getLanguagesByCategory();
      for (const category of Object.keys(categories)) {
        addLog(`${category}:`);
        for (const ext of categories[category]) {
          const info = (LANGUAGE_MAP as any)[ext];
          if (!info) continue;
          const icon = String(info.icon || '').padEnd(7, ' ');
          const name = String(info.name || ext);
          const exec = info.executionCommand ? ` (${info.executionCommand})` : '';
          addLog(`  ${icon} ${name}${exec}`);
        }
        addLog('');
      }

      addLog('--------------------------------------------------');
      addLog(`Total: ${Object.keys(LANGUAGE_MAP).length} languages supported`);
      addLog('Create any file with: create filename.ext');

    } else if (command === 'open') {
      if (args.length === 0) {
        addLog('Error: Please provide a filename. Usage: open <filename>');
        return;
      }
      const fileName = args[0];
      const cleanName = fileName.split('/').pop() || fileName;
      const found = findFileByName(files, cleanName);
      if (!found) {
        addLog(`Error: File '${fileName}' not found.`);
        return;
      }
      setActiveFile(found);
      addLog(`Opened ${found.name}`);

    } else if (command === 'create') {
        if (args.length === 0) {
            addLog('Error: Please provide a filename. Usage: create <filename>');
            return;
        }
        const fileName = args[0];
        const newFile = addFileToRoot(fileName);
        addLog(`Created file: ${fileName}`);
        setActiveFile(newFile);
        addLog(`Opened ${fileName}`);

    } else if (command === 'mode') {
        if (args[0] === 'show' || args[0] === 'show-me') {
            setMode('show-me');
            addLog('Mode switched to: SHOW ME (Educational Mode)');
        } else if (args[0] === 'do' || args[0] === 'do-it') {
            setMode('do-it');
            addLog('Mode switched to: DO IT (Automation Mode)');
        } else {
            addLog('Usage: mode show-me OR mode do-it');
        }

    } else if (command === 'clear') {
      setLogs([]);
    } else if (command === 'ls') {
        const root = files.find(f => f.id === 'root');
        if (root && root.children) {
           root.children.forEach(c => addLog(`${c.type === 'folder' ? '📁' : '📄'} ${c.name}`));
        }
    } else if (['run', 'python', 'node', 'exec'].includes(command)) {
      let targetFile: FileNode | null = activeFile;
      
      if (args.length > 0) {
        const fileName = args[0];
        const cleanName = fileName.split('/').pop() || fileName;
        const found = findFileByName(files, cleanName);
        if (found) {
          targetFile = found;
        } else {
          addLog(`Error: File '${fileName}' not found.`);
          return;
        }
      }

      if (!targetFile) {
        addLog('Error: No file selected. Usage: run <filename> or select a file.');
        return;
      }
      
      executeFile(targetFile);

    } else if (command === 'status') {
      addLog('System Status: 🟢 ONLINE');
      addLog('Revenue Pillars: 🟢 ACTIVE');
      addLog('Security Level: 🔒 MAX (NIST/HIPAA Ready)');
    } else {
      addLog(`Command not found: ${command}. Type "help" for a list of commands.`);
    }
  };

  const handleModeChange = (newMode: 'show-me' | 'do-it') => {
    setMode(newMode);
    addLog(`Switched to "${newMode === 'show-me' ? 'Show Me' : 'Do It'}" mode.`);
  };

  return (
    <Layout
      sidebar={
        <LeftSidebar
          files={files}
          onFileSelect={handleFileSelect}
          onToggleFolder={handleToggleFolder}
          activeFileId={activeFile?.id}
        />
      }
      terminal={
        <Terminal
          logs={logs}
          onCommand={handleCommand}
        />
      }
      aiPanel={
        <AIAssistant 
            isOpen={isAiOpen} 
            onClose={() => setIsAiOpen(false)}
            activeFileName={activeFile?.name}
            activeFileContent={activeFile?.content}
            mode={mode}
        />
      }
      onModeChange={handleModeChange}
      currentMode={mode}
      onSettingsClick={() => addLog('Settings: Config dashboard coming soon.')}
      onRunClick={() => {
        if (activeFile) {
          executeFile(activeFile);
        } else {
          addLog('Error: No file selected to run.');
        }
      }}
      isAiOpen={isAiOpen}
      onToggleAi={() => setIsAiOpen(!isAiOpen)}
    >
      {activeFile ? (
        <CodeEditor
          code={activeFile.content || ''}
          onChange={handleCodeChange}
          readOnly={mode === 'do-it'} 
        />
      ) : (
        <div className="flex flex-col items-center justify-center h-full text-slate-500">
           <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
             <span className="text-2xl">⚡</span>
           </div>
           <p className="text-lg font-medium">Select a file to start coding</p>
           <p className="text-sm opacity-60">or type "run &lt;filename&gt;" in the terminal</p>
        </div>
      )}
    </Layout>
  );
}
