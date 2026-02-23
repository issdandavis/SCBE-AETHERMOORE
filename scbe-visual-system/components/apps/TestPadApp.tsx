/**
 * SCBE Test Pad - Sandboxed npm Testing UI
 *
 * Provides a code editor, npm command controls, governance status panel,
 * and output viewer. Integrates with the hyperbolic containment module
 * for pre-execution risk assessment.
 *
 * @license Apache-2.0
 * USPTO #63/961,403
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Play, Square, Package, Shield, AlertTriangle, CheckCircle,
  Terminal, FileCode, Trash2, Download, Activity, Circle,
  ChevronDown, RefreshCw, Layers, Zap
} from 'lucide-react';
import {
  checkContainment,
  type ContainmentResult,
  type CodeVector,
  analyzeCodeVector,
  preflightCheck,
  createSession,
  closeSession,
  formatResult,
  DEFAULT_PACKAGE_JSON,
  type TestCommand,
  type TestPadSession,
  type SandboxResult,
} from '../../src/testpad';

// ---------- Constants ----------

const COMMANDS: { cmd: TestCommand; label: string; icon: React.ElementType; color: string }[] = [
  { cmd: 'install', label: 'Install', icon: Download, color: 'bg-blue-600 hover:bg-blue-500' },
  { cmd: 'test', label: 'Test', icon: CheckCircle, color: 'bg-emerald-600 hover:bg-emerald-500' },
  { cmd: 'run', label: 'Run', icon: Play, color: 'bg-amber-600 hover:bg-amber-500' },
  { cmd: 'build', label: 'Build', icon: Package, color: 'bg-purple-600 hover:bg-purple-500' },
  { cmd: 'lint', label: 'Lint', icon: FileCode, color: 'bg-cyan-600 hover:bg-cyan-500' },
];

const PHI = 1.618033988749895;

const INITIAL_CODE = `// SCBE Test Pad - Write your code here
// The containment module will analyze it in real-time

const greet = (name) => {
  console.log(\`Hello, \${name}! Welcome to SCBE.\`);
};

greet("Aethermoor");
`;

// ---------- Sub-components ----------

const GovernanceBar: React.FC<{ containment: ContainmentResult | null; vector: CodeVector | null }> = ({ containment, vector }) => {
  if (!containment) {
    return (
      <div className="px-4 py-2 bg-zinc-800/50 border-b border-zinc-700 flex items-center gap-3 text-zinc-500 text-xs">
        <Shield size={14} />
        <span className="font-mono">Awaiting input...</span>
      </div>
    );
  }

  const isAllowed = containment.allowed;
  const distPct = Math.min(100, (containment.distance / PHI) * 100);
  const riskColor = containment.riskScore < 2 ? 'text-emerald-400' : containment.riskScore < 5 ? 'text-amber-400' : 'text-red-400';
  const statusColor = isAllowed ? 'text-emerald-400' : 'text-red-400';
  const statusBg = isAllowed ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30';

  return (
    <div className={`px-4 py-2 border-b border-zinc-700 ${statusBg}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Status badge */}
          <div className={`flex items-center gap-2 ${statusColor} text-xs font-bold uppercase tracking-wider`}>
            {isAllowed ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
            {isAllowed ? 'ALLOW' : 'DENY'}
          </div>

          {/* Hyperbolic distance bar */}
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="font-mono">d*={containment.distance.toFixed(3)}</span>
            <div className="w-24 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${distPct > 90 ? 'bg-red-500' : distPct > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${distPct}%` }}
              />
            </div>
            <span className="font-mono text-zinc-500">φ={PHI.toFixed(3)}</span>
          </div>

          {/* Risk score */}
          <div className={`flex items-center gap-1 text-xs font-mono ${riskColor}`}>
            <Activity size={12} />
            H(d*)={containment.riskScore.toFixed(2)}
          </div>

          {/* Breath factor */}
          <div className="flex items-center gap-1 text-xs font-mono text-zinc-400">
            <Zap size={12} />
            β={containment.breathFactor.toFixed(3)}
          </div>
        </div>

        {/* Violations count */}
        {containment.violations.length > 0 && (
          <div className="flex items-center gap-1 text-xs text-red-400">
            <AlertTriangle size={12} />
            {containment.violations.length} violation{containment.violations.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Vector breakdown (collapsed by default) */}
      {vector && (
        <div className="mt-1 flex gap-3 text-[10px] font-mono text-zinc-500">
          <span>cx={vector.complexity.toFixed(2)}</span>
          <span>dp={vector.depth.toFixed(2)}</span>
          <span>io={vector.ioWeight.toFixed(2)}</span>
          <span>cr={vector.cryptoWeight.toFixed(2)}</span>
          <span>ps={vector.processWeight.toFixed(2)}</span>
          <span>dy={vector.dynamicWeight.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
};

const OutputPanel: React.FC<{ output: string[]; isRunning: boolean }> = ({ output, isRunning }) => (
  <div className="flex-1 bg-black/40 border-t border-zinc-800 flex flex-col min-h-0">
    <div className="px-4 py-1.5 border-b border-zinc-800 flex items-center justify-between">
      <div className="flex items-center gap-2 text-zinc-500 text-[10px] uppercase tracking-widest font-bold">
        <Terminal size={12} />
        Output
      </div>
      {isRunning && (
        <div className="flex items-center gap-2 text-amber-400 text-[10px]">
          <RefreshCw size={10} className="animate-spin" />
          Running...
        </div>
      )}
    </div>
    <div className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
      {output.length === 0 ? (
        <div className="text-zinc-600 italic">Run a command to see output here...</div>
      ) : (
        output.map((line, i) => (
          <div
            key={i}
            className={`mb-0.5 ${
              line.startsWith('---') ? 'text-sky-400 font-bold mt-2' :
              line.startsWith('  !') ? 'text-red-400' :
              line.startsWith('Status: PASS') ? 'text-emerald-400' :
              line.startsWith('Status: FAIL') ? 'text-red-400' :
              line.startsWith('Containment: DENIED') ? 'text-red-400' :
              line.startsWith('Containment: ALLOWED') ? 'text-emerald-400' :
              'text-zinc-300'
            }`}
          >
            {line}
          </div>
        ))
      )}
    </div>
  </div>
);

// ---------- Main Component ----------

export const TestPadApp: React.FC = () => {
  const [code, setCode] = useState(INITIAL_CODE);
  const [packageJson, setPackageJson] = useState(DEFAULT_PACKAGE_JSON);
  const [activeTab, setActiveTab] = useState<'code' | 'package'>('code');
  const [containment, setContainment] = useState<ContainmentResult | null>(null);
  const [vector, setVector] = useState<CodeVector | null>(null);
  const [output, setOutput] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [session, setSession] = useState<TestPadSession | null>(null);
  const [auditExpanded, setAuditExpanded] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initialize session
  useEffect(() => {
    const s = createSession(packageJson, code);
    setSession(s);
    return () => { if (s) closeSession(s.id); };
  }, []);

  // Real-time containment analysis (debounced)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (code.trim()) {
        const v = analyzeCodeVector(code);
        setVector(v);
        const result = checkContainment(code, 'run');
        setContainment(result);
      } else {
        setVector(null);
        setContainment(null);
      }
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [code]);

  // Execute command
  const handleRun = useCallback(async (cmd: TestCommand) => {
    const preflight = preflightCheck(code, cmd);

    setOutput(prev => [
      ...prev,
      '',
      `--- npm ${cmd} (${new Date().toLocaleTimeString()}) ---`,
      ...preflight.containment.auditLog.split('\n'),
      '',
    ]);

    if (!preflight.containment.allowed) {
      setOutput(prev => [
        ...prev,
        `BLOCKED: Containment denied execution.`,
        `Hyperbolic distance ${preflight.containment.distance.toFixed(4)} exceeds PHI boundary (${PHI.toFixed(4)}).`,
        ...preflight.containment.violations.map(v => `  ! ${v}`),
      ]);
      return;
    }

    setIsRunning(true);

    // In Electron, this would go through IPC to main process.
    // In browser, we simulate.
    const isElectron = !!(window as any).scbeElectron;

    if (isElectron) {
      try {
        const result = await (window as any).scbeElectron.testpad.execute(code, cmd, preflight.config);
        const formatted = formatResult(result);
        setOutput(prev => [...prev, ...formatted.split('\n')]);
        if (session) session.results.push(result);
      } catch (err: any) {
        setOutput(prev => [...prev, `ERROR: ${err.message || 'Execution failed'}`]);
      }
    } else {
      // Browser simulation
      setOutput(prev => [...prev, `[Simulation] npm ${cmd} would execute in Electron sandbox.`]);
      await new Promise(r => setTimeout(r, 800));
      setOutput(prev => [
        ...prev,
        `[Simulation] Exit code: 0`,
        `[Simulation] Duration: ${Math.floor(Math.random() * 2000 + 500)}ms`,
        `[Simulation] Containment: ALLOWED (d*=${preflight.containment.distance.toFixed(4)})`,
      ]);
    }

    setIsRunning(false);
  }, [code, session]);

  const clearOutput = useCallback(() => setOutput([]), []);

  return (
    <div className="h-full w-full bg-[#1a1a2e] flex flex-col text-zinc-300">
      {/* Toolbar */}
      <div className="px-4 py-2 bg-[#16213e] border-b border-zinc-700 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-sky-400 uppercase tracking-widest">
            <Shield size={14} />
            SCBE Test Pad
          </div>
          {session && (
            <span className="text-[10px] font-mono text-zinc-500">{session.id}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Command buttons */}
          {COMMANDS.map(({ cmd, label, icon: Icon, color }) => (
            <button
              key={cmd}
              onClick={() => handleRun(cmd)}
              disabled={isRunning || !containment?.allowed}
              className={`px-3 py-1.5 ${color} text-white rounded-lg text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors`}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
          <div className="w-px h-6 bg-zinc-700 mx-1" />
          <button
            onClick={clearOutput}
            className="p-2 hover:bg-zinc-700 rounded-lg text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Clear output"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Governance Bar */}
      <GovernanceBar containment={containment} vector={vector} />

      {/* Main content: Editor + Output */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Editor area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* File tabs */}
          <div className="flex border-b border-zinc-800">
            <button
              onClick={() => setActiveTab('code')}
              className={`px-4 py-2 text-[10px] font-bold uppercase tracking-widest flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === 'code'
                  ? 'border-sky-500 text-sky-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <FileCode size={12} />
              index.js
            </button>
            <button
              onClick={() => setActiveTab('package')}
              className={`px-4 py-2 text-[10px] font-bold uppercase tracking-widest flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === 'package'
                  ? 'border-sky-500 text-sky-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <Package size={12} />
              package.json
            </button>
          </div>

          {/* Code editor */}
          <textarea
            value={activeTab === 'code' ? code : packageJson}
            onChange={(e) => activeTab === 'code' ? setCode(e.target.value) : setPackageJson(e.target.value)}
            className="flex-1 bg-transparent p-4 font-mono text-sm resize-none focus:outline-none scrollbar-thin scrollbar-thumb-zinc-700 leading-relaxed"
            spellCheck={false}
            placeholder={activeTab === 'code' ? '// Write your code here...' : '{ "name": "my-project" }'}
          />
        </div>

        {/* Output panel */}
        <OutputPanel output={output} isRunning={isRunning} />
      </div>

      {/* Audit log expandable */}
      {containment && (
        <button
          onClick={() => setAuditExpanded(!auditExpanded)}
          className="px-4 py-1.5 bg-zinc-900 border-t border-zinc-800 flex items-center gap-2 text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <Layers size={10} />
          <span className="uppercase tracking-widest font-bold">Audit Log</span>
          <ChevronDown size={10} className={`transition-transform ${auditExpanded ? 'rotate-180' : ''}`} />
        </button>
      )}
      {auditExpanded && containment && (
        <div className="max-h-32 overflow-y-auto px-4 py-2 bg-zinc-900/80 border-t border-zinc-800 font-mono text-[10px] text-zinc-500 leading-relaxed">
          {containment.auditLog.split('\n').map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
};
