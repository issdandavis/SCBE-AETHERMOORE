import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const systems = [
  {
    id: 'machine-crystal',
    label: 'Machine Crystal',
    short: 'Geometric Turing object',
    status: 'PASS',
    command: 'python scripts/system/review_machine_crystal_area.py',
    output: [
      'verdict: PASS',
      'primitive +++. -> output_hex 03',
      'higher copy_emit_cases: 65 / 65',
      'safe path: EXECUTED -> output_hex 05',
      'risk path: COMPILED_NOT_EXECUTED',
    ],
    receipt: 'artifacts/machine_crystal/area_review.json',
    link: 'research/MACHINE_CRYSTAL_GEOMETRY_RELATION_MAP_2026-06-27.md',
    caution: '128 unique hashes means distinct programs, not a proof of full quasicrystal order.',
    color: 'mint',
  },
  {
    id: 'compiler-lane',
    label: 'Compiler Lane',
    short: 'Words -> opcodes -> code',
    status: 'WIRED',
    command: 'python scripts/system/run_scbe_compiler_lane.py --opcodes 0x00 --target python',
    output: [
      "bip'a binds to ADD",
      "klik'ra binds to CLAMP",
      'UTF transfer gate has a spec surface',
      'unknown words route to lexicon, not guessing',
    ],
    receipt: 'docs/specs/UTF_PYTHON_TRANSFER_GATE_2026-06-27.md',
    link: 'specs/UTF_PYTHON_TRANSFER_GATE_2026-06-27.md',
    caution: 'The website demonstrates the lane; actual compilation remains a repo/runtime action.',
    color: 'gold',
  },
  {
    id: 'pne-cube',
    label: 'p/n/e Cube',
    short: 'Particle conservation rails',
    status: 'PASS',
    command: 'python -m python.scbe.machine_crystal_pne_cube',
    output: [
      'beta-minus: neutron -> proton accepted',
      'alpha / fusion / fission examples balance',
      'invalid nucleon creation rejected',
      'chemistry is electron-axis only; nuclear uses full cube',
    ],
    receipt: 'artifacts/machine_crystal/pne_cube.json',
    link: 'research/MACHINE_CRYSTAL_PNE_CUBE_2026-06-27.md',
    caution: 'Small conservation-gate example set, not a full chemistry or nuclear database.',
    color: 'blue',
  },
  {
    id: 'particle-chem',
    label: 'Particle Chem',
    short: 'Balancer plus valence rung',
    status: 'PASS',
    command: 'python -m python.scbe.machine_crystal_particle_chem',
    output: [
      'balanced cases accepted',
      'coefficients match expected',
      'invalid case rejected',
      'valence rung is route annotation',
    ],
    receipt: 'artifacts/machine_crystal/particle_chem.json',
    link: 'research/MACHINE_CRYSTAL_PARTICLE_CHEM_2026-06-27.md',
    caution: 'Exact balance is real; valence rung is a heuristic, not a stability proof.',
    color: 'rose',
  },
  {
    id: 'instrument-computer',
    label: 'Instrument Computer',
    short: 'Tab, reel, shell, Holophonor',
    status: 'PASS',
    command: 'python scripts\\audio\\instrument_computer.py demo',
    output: [
      'stateful reel RAM persists across plays',
      'demo outputs: reel 05, shell 0a',
      'shape-chords + guitar package: 10 pytest checks passed',
      'Haskell primary face present; STISTA atom class present',
    ],
    receipt: 'docs/research/INSTRUMENT_COMPUTER_README_2026-06-27.md',
    link: 'research/INSTRUMENT_COMPUTER_README_2026-06-27.md',
    caution: 'The package executes through the verified core; instruments are interfaces, not magic memory machines.',
    color: 'gold',
  },
  {
    id: 'training-room',
    label: 'Training Room',
    short: 'Computer-use mission board',
    status: 'DESIGNED',
    command: 'open docs/training/* and route tasks through AetherDesk',
    output: [
      'browser-use guide linked',
      'computer-use loop linked',
      'code adventure assignments linked',
      'small LLM service guide linked',
    ],
    receipt: 'docs/training/AETHERDESK_COMPUTER_USE_TRAINING_LOOP_2026-06-27.md',
    link: 'training/AETHERDESK_COMPUTER_USE_TRAINING_LOOP_2026-06-27.md',
    caution: 'Training launch remains gated; no paid run starts from this static site.',
    color: 'violet',
  },
  {
    id: 'live-coding',
    label: 'Live Coding Bridge',
    short: 'Haskell face -> Tidal adapter',
    status: 'TARGET',
    command: 'song -> op bytes -> haskell face -> tidal pattern',
    output: [
      'live coding is prior art, not our novelty',
      'Haskell face is verified down to op bytes',
      'TidalCycles speaks Haskell-family pattern composition',
      'next receipt target: Tidal pattern emitter',
    ],
    receipt: 'docs/research/INSTRUMENT_COMPUTER_README_2026-06-27.md',
    link: 'research/INSTRUMENT_COMPUTER_README_2026-06-27.md',
    caution: 'This page marks Tidal as the adapter target; it does not claim Tidal execution yet.',
    color: 'blue',
  },
];

const apps = [
  { id: 'browser', name: 'Browser', sub: 'Research, docs, receipts' },
  { id: 'terminal', name: 'Terminal', sub: 'Allowlisted commands' },
  { id: 'powershell', name: 'PowerShell', sub: 'Windows operator lane' },
  { id: 'writer', name: 'Writer', sub: 'Book and guide drafting' },
  { id: 'compiler', name: 'Compiler', sub: 'Conlang and opcode lanes' },
  { id: 'guitar', name: 'Guitar Tab', sub: 'Instrument computer' },
  { id: 'proof', name: 'Proof Drawer', sub: 'Artifacts and caveats' },
  { id: 'colab', name: 'Colab Prep', sub: 'Notebook launch plans' },
  { id: 'hf', name: 'HF Jobs', sub: 'Token-safe training prep' },
];

const missions = [
  {
    title: 'Adventure/code assignment',
    body: 'Fill blanks, choose route, run validator, score outcome against schematic stats.',
    link: 'training/CODE_ADVENTURE_ASSIGNMENT_SYSTEM_2026-06-27.md',
  },
  {
    title: 'Iridescent provenance text',
    body: 'Color-tag human words, AI text, verified research, facts, feelings, and correction pairs.',
    link: 'specs/IRIDESCENT_PROVENANCE_TEXT_SCHEMA_2026-06-27.md',
  },
  {
    title: 'Small LLM service guide',
    body: 'Teach a small model how to use APIs, Colab, HF, browser tasks, and scripted routines.',
    link: 'training/SMALL_LLM_SERVICE_USER_GUIDE_2026-06-27.md',
  },
];

const instrumentExamples = [
  ['Piano', '12 notes', '1 note/op', '5'],
  ['Bagpipe', '9 notes', '1 note/op', '5'],
  ['Harp', '7 notes', '1 note/op', '5'],
  ['Guzheng', '5 notes', '2 notes/op', '5'],
  ['Whistle', '2 tones', '3 notes/op', '5'],
];

const packageReceipts = [
  ['CLI', 'python scripts/audio/instrument_computer.py demo'],
  ['Validation', '10 pytest checks passed'],
  ['Reel RAM', 'E E E E E loads 5; loop doubles; G D outputs 10'],
  ['Faces', 'primary 8, broad 18, Haskell face present'],
  ['Shell', 'stateful command hole returns 0a'],
  ['Holophonor', 'first_song.wav embedded as playable site audio'],
];

const offerCards = [
  {
    title: 'Try the desk',
    price: 'free static demo',
    body: 'Use Polly, play the music compiler, inspect receipts, and see the governed workbench flow.',
    action: 'Open live desk',
    href: '#station',
  },
  {
    title: 'Proof workbench',
    price: 'operator toolkit',
    body: 'Turn claims into runnable commands, artifacts, caveats, and release-review receipts.',
    action: 'Open proof workbench',
    href: 'proof-workbench.html',
  },
  {
    title: 'Paid pilot',
    price: 'setup + integration',
    body: 'Wire AetherDesk around your workflow: browser, terminal, training guide, docs, and receipts.',
    action: 'Book setup',
    href: 'mailto:ai@aethermoore.com?subject=AetherDesk%20paid%20pilot',
  },
];

const puddingSteps = [
  ['Ask Polly', 'sidebar answers from page state and can speak'],
  ['Play notes', 'notes compile to Brainfuck and output 5'],
  ['Route a face', 'Machine Crystal selector changes the operation face'],
  ['Open receipt', 'proof links stay attached to each claim'],
];

const knifeProof = [
  ['base 0.5B balance', '0.00'],
  ['chem adapter balance', '0.00'],
  ['measured delta', '+0.00'],
  ['business conclusion', 'verifier is the value'],
];

const liveCodingBridge = [
  ['Established field', 'TidalCycles, Sonic Pi, Strudel, ChucK, SuperCollider'],
  ['Our actual bridge', 'played notes -> op bytes -> verified core -> Haskell face'],
  ['Next adapter', 'emit a TidalCycles pattern from the Haskell/op stream'],
  ['18-face shape', 'an octadecagonal language hub: one op node, eighteen emitted language faces'],
];

const holophonorTrack = './audio/first_song.wav';

const noteKeys = [
  { note: 'C4', hz: 261.63, op: '+', role: 'increment' },
  { note: 'D4', hz: 293.66, op: '>', role: 'move right' },
  { note: 'E4', hz: 329.63, op: '<', role: 'move left' },
  { note: 'F4', hz: 349.23, op: '-', role: 'decrement' },
  { note: 'G4', hz: 392.0, op: '[', role: 'open loop' },
  { note: 'A4', hz: 440.0, op: ']', role: 'close loop' },
  { note: 'B4', hz: 493.88, op: '.', role: 'output' },
  { note: 'C5', hz: 523.25, op: ',', role: 'input' },
];

const phraseBook = {
  count4: ['C4', 'C4', 'C4', 'C4', 'B4'],
  add23: ['C4', 'C4', 'D4', 'C4', 'C4', 'C4', 'G4', 'E4', 'C4', 'D4', 'F4', 'A4', 'E4', 'B4'],
  double3: ['C4', 'C4', 'C4', 'G4', 'D4', 'C4', 'C4', 'E4', 'F4', 'A4', 'D4', 'B4'],
};

const musicResources = [
  ['Tone.js', 'MIT', 'Web Audio synths, effects, transport', 'https://github.com/tonejs/tone.js/'],
  ['abcjs', 'MIT', 'ABC notation render/playback in browser', 'https://www.abcjs.net/'],
  ['VexFlow', 'Open source', 'Sheet music and guitar tablature rendering', 'https://www.vexflow.com/'],
  ['music21', 'BSD-3', 'Python computational musicology toolkit', 'https://github.com/cuthbertlab/music21'],
  ['Magenta.js', 'Apache-2.0', 'Browser ML music experiments', 'https://github.com/magenta/magenta-js'],
];

const benchmarkRows = [
  ['Proof assistants', 'Very high proof rigor', 'Slow formalization', 'Use for theorem-grade claims'],
  ['Compilers', 'Exact build result', 'Only proves emitted program', 'Use as the oven for code'],
  ['Notebooks', 'Fast experiments', 'State drift and hidden setup', 'Use with receipts'],
  ['Boot.dev style learning', 'Mission progression', 'Not enough product context alone', 'Clone the loop, add AI mentor'],
  ['SCBE / AetherDesk', 'Outcome + receipt + repair', 'Still needs hidden evals', 'Use as governed work room'],
];

const pollyModes = [
  ['operator', 'Operator'],
  ['crystal', 'Crystal guide'],
  ['training', 'Training coach'],
];

const pollyQuickPrompts = [
  'What works on this page?',
  'How do I run the music compiler?',
  'What is the knife test?',
  'What is the safest next step?',
];

function notesToProgram(notes) {
  return notes.map((note) => noteKeys.find((key) => key.note === note)?.op ?? '').join('');
}

function runBrainfuck(program) {
  const tape = new Uint8Array(128);
  const output = [];
  const bracket = new Map();
  const stack = [];
  for (let i = 0; i < program.length; i += 1) {
    if (program[i] === '[') stack.push(i);
    if (program[i] === ']') {
      const open = stack.pop();
      if (open === undefined) return { ok: false, message: 'unmatched close loop', tape0: tape[0], output };
      bracket.set(open, i);
      bracket.set(i, open);
    }
  }
  if (stack.length) return { ok: false, message: 'unmatched open loop', tape0: tape[0], output };
  let pointer = 0;
  let pc = 0;
  let steps = 0;
  while (pc < program.length && steps < 10000) {
    const op = program[pc];
    if (op === '+') tape[pointer] = (tape[pointer] + 1) & 255;
    if (op === '-') tape[pointer] = (tape[pointer] - 1) & 255;
    if (op === '>') pointer = Math.min(pointer + 1, tape.length - 1);
    if (op === '<') pointer = Math.max(pointer - 1, 0);
    if (op === '.') output.push(tape[pointer]);
    if (op === '[' && tape[pointer] === 0) pc = bracket.get(pc);
    if (op === ']' && tape[pointer] !== 0) pc = bracket.get(pc);
    pc += 1;
    steps += 1;
  }
  if (steps >= 10000) return { ok: false, message: 'step limit hit', tape0: tape[0], output };
  return { ok: true, message: `ran ${steps} steps`, tape0: tape[0], output };
}

function buildPollyReply(input, mode, active, compiledProgram, programResult) {
  const text = input.toLowerCase();
  if (!input.trim()) return 'Give me a concrete task. I can explain the active system, route you to a doc, or help run the music compiler.';
  if (text.includes('music') || text.includes('keyboard') || text.includes('song') || text.includes('compiler')) {
    return `Music compiler route: press a note, load a phrase, then compile and run. Current program is ${compiledProgram || '(empty)'}. Current result is ${programResult.ok ? `PASS, tape0 ${programResult.tape0}, output [${programResult.output.join(',')}]` : programResult.message}.`;
  }
  if (text.includes('picture') || text.includes('image') || text.includes('photo')) {
    return 'Picture review: the rock, garden, and notebook images are good atmosphere, but they are not proof. I keep them as mood art and keep real claims in receipts, commands, and runnable widgets.';
  }
  if (text.includes('crystal') || text.includes('shape') || text.includes('geometry')) {
    return 'Machine Crystal route: eight visible faces map to Brainfuck operations. It is useful because shapes become controls, but the execution claim stays anchored to the verified core and receipts.';
  }
  if (text.includes('train') || text.includes('small llm') || text.includes('guide')) {
    return 'Training route: use the mission cards. The small-model guide should teach APIs, browser tasks, Colab/HF routines, and validation habits with fill-in blanks and scored outcomes.';
  }
  if (text.includes('knife') || text.includes('adapter') || text.includes('0.5b') || text.includes('verifier')) {
    return 'Knife test: base 0.5B and the chemistry adapter both scored 0.00 balance on this conservation gate, so the adapter showed no measured lift here. The product lesson is that the verifier is the blade: the model proposes, the substrate checks, and trust comes from receipts.';
  }
  if (text.includes('safe') || text.includes('next')) {
    return `Safest next step: keep ${active.label} selected, run the browser-side route, then open the linked receipt. If it does not emit a receipt, treat it as design, not a shipped claim.`;
  }
  if (mode === 'crystal') {
    return `Crystal guide: ${active.label} is selected. Its command is "${active.command}". Its boundary is: ${active.caution}`;
  }
  if (mode === 'training') {
    return 'Training coach: turn the task into a mission, add a blank to fill, add one multiple-choice route, run the validator, then score the output against the schematic.';
  }
  return `I am Polly in local site mode. Active room: ${active.label}. Status: ${active.status}. Ask about pictures, music compiler, training, safety, or the Machine Crystal.`;
}

function App() {
  const [activeId, setActiveId] = useState('machine-crystal');
  const [booted, setBooted] = useState(false);
  const [face, setFace] = useState(2);
  const [log, setLog] = useState([]);
  const [playedNotes, setPlayedNotes] = useState(phraseBook.add23);
  const [programResult, setProgramResult] = useState(() => runBrainfuck(notesToProgram(phraseBook.add23)));
  const [activeAppId, setActiveAppId] = useState('browser');
  const [deskCommand, setDeskCommand] = useState('help');
  const [deskOutput, setDeskOutput] = useState(['AetherDesk terminal ready.', 'Try: help, status, compile add23, proof, polly']);
  const [deskNote, setDeskNote] = useState('Morning objective: use AetherDesk as the live PC, run the thing, keep the receipt.');
  const [pollyOpen, setPollyOpen] = useState(false);
  const [pollyMode, setPollyMode] = useState('operator');
  const [pollyInput, setPollyInput] = useState('');
  const [pollyMessages, setPollyMessages] = useState([
    {
      role: 'assistant',
      text: 'I am Polly. This sidebar now works locally: pick a mode, ask a question, and I will answer from the page state.',
    },
  ]);
  const active = useMemo(() => systems.find((s) => s.id === activeId) ?? systems[0], [activeId]);
  const activeApp = useMemo(() => apps.find((app) => app.id === activeAppId) ?? apps[0], [activeAppId]);
  const compiledMusicProgram = useMemo(() => notesToProgram(playedNotes), [playedNotes]);

  function runRoute() {
    setBooted(true);
    const stamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLog((prev) => [
      { stamp, label: active.label, command: active.command, result: active.output[0] },
      ...prev,
    ].slice(0, 6));
  }

  function runDeskCommand(event) {
    event.preventDefault();
    const raw = deskCommand.trim();
    const cmd = raw.toLowerCase();
    let lines = [];
    if (!cmd || cmd === 'help') {
      lines = ['commands: help, status, compile add23, proof, polly', 'static safety: this terminal updates the browser UI only'];
    } else if (cmd === 'status') {
      lines = [`active system: ${active.label}`, `active app: ${activeApp.name}`, `music program: ${compiledMusicProgram || '(empty)'}`];
    } else if (cmd === 'compile add23') {
      loadPhrase('add23');
      lines = ['loaded add 2+3 phrase', 'program: ++>+++[<+>-]<.', 'expected browser output: [5]'];
    } else if (cmd === 'proof') {
      setActiveAppId('proof');
      lines = [`receipt: ${active.receipt}`, `boundary: ${active.caution}`];
    } else if (cmd === 'polly') {
      setPollyOpen(true);
      lines = ['opened Polly sidebar', 'ask: What works on this page?'];
    } else {
      lines = [`unknown allowlisted command: ${raw}`, 'try: help'];
    }
    setDeskOutput([`$ ${raw || 'help'}`, ...lines]);
    setDeskCommand('');
  }

  function renderDeskApp() {
    if (activeAppId === 'browser') {
      return (
        <div className="pc-browser">
          <div className="pc-address mono">aetherdesk://home/process-first</div>
          <div className="pc-card-grid">
            <a href="#offers"><b>Use / Buy</b><span>Try, proof, or book setup</span></a>
            <a href="#music-keyboard"><b>Music compiler</b><span>Play notes into code</span></a>
            <a href="#live-coding"><b>Live coding bridge</b><span>Haskell face to Tidal target</span></a>
            <a href={active.link}><b>Active receipt</b><span>{active.label}</span></a>
          </div>
        </div>
      );
    }
    if (activeAppId === 'terminal') {
      return (
        <div className="pc-terminal">
          <div className="terminal-lines mono live-lines">
            {deskOutput.map((line) => <p key={line}><span>{line.startsWith('$') ? '$' : '>'}</span> {line.replace(/^\$ /, '')}</p>)}
          </div>
          <form className="pc-command" onSubmit={runDeskCommand}>
            <input value={deskCommand} onChange={(event) => setDeskCommand(event.target.value)} placeholder="help" />
            <button type="submit">run</button>
          </form>
        </div>
      );
    }
    if (activeAppId === 'powershell') {
      return (
        <div className="pc-list">
          <p className="pc-copy">PowerShell lane is command-prep only on the public site. It shows safe commands; it does not execute host shell from GitHub Pages.</p>
          {[
            'npm run build',
            'python scripts/audio/instrument_computer.py demo',
            'python scripts/system/review_machine_crystal_area.py',
            'python -m pytest tests/audio/test_instrument_computer_package.py -q',
          ].map((cmd) => <code key={cmd}>{cmd}</code>)}
        </div>
      );
    }
    if (activeAppId === 'writer') {
      return (
        <div className="pc-writer">
          <textarea value={deskNote} onChange={(event) => setDeskNote(event.target.value)} />
          <div className="pc-stats mono"><span>{deskNote.split(/\s+/).filter(Boolean).length} words</span><span>autosaved in page state</span></div>
        </div>
      );
    }
    if (activeAppId === 'compiler') {
      return (
        <div className="pc-list">
          <p className="pc-copy">Compiler lane maps words and notes to the verified op-core.</p>
          <code>{"bip'a -> ADD -> 0x00"}</code>
          <code>{"klik'ra -> CLAMP -> 0x29"}</code>
          <code>{`notes -> ${compiledMusicProgram || '(empty)'}`}</code>
          <button className="pc-action" onClick={() => { setActiveId('compiler-lane'); setDeskOutput(['$ load compiler', 'compiler-lane selected', "bip'a maps to ADD"]); }}>load compiler context</button>
        </div>
      );
    }
    if (activeAppId === 'guitar') {
      return (
        <div className="pc-list">
          <p className="pc-copy">Instrument computer state is live in this browser.</p>
          <code>current program: {compiledMusicProgram || '(empty)'}</code>
          <code>result: {programResult.ok ? `tape0 ${programResult.tape0}, output [${programResult.output.join(',')}]` : programResult.message}</code>
          <button className="pc-action" onClick={() => { loadPhrase('add23'); setLog((prev) => [{ stamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), label: 'Guitar Tab', command: 'load add23', result: 'output [5]' }, ...prev].slice(0, 6)); }}>load and run add 2+3</button>
        </div>
      );
    }
    if (activeAppId === 'proof') {
      return (
        <div className="pc-list">
          <p className="pc-copy">{active.caution}</p>
          <code>{active.command}</code>
          <code>{active.receipt}</code>
          <a className="pc-action" href={active.link}>open linked receipt</a>
        </div>
      );
    }
    if (activeAppId === 'colab') {
      return (
        <div className="pc-list">
          <p className="pc-copy">Colab prep is staged work: notebooks and scripts can be launched later, but this page does not start paid compute.</p>
          <code>prepare notebook</code>
          <code>attach dataset receipt</code>
          <code>run only after approval</code>
        </div>
      );
    }
    if (activeAppId === 'hf') {
      return (
        <div className="pc-list">
          <p className="pc-copy">HF jobs stay token-safe. Browser sees status and metadata only; tokens belong server-side.</p>
          <code>HF_TOKEN: server only</code>
          <code>OAuth client id: public metadata</code>
          <code>job list: safe JSON</code>
        </div>
      );
    }
    return null;
  }

  function speakPolly(text) {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.94;
    utterance.pitch = 1.02;
    window.speechSynthesis.speak(utterance);
  }

  function sendPolly(message = pollyInput) {
    const trimmed = message.trim();
    if (!trimmed) return;
    const reply = buildPollyReply(trimmed, pollyMode, active, compiledMusicProgram, programResult);
    setPollyMessages((prev) => [...prev, { role: 'user', text: trimmed }, { role: 'assistant', text: reply }].slice(-10));
    setPollyInput('');
    speakPolly(reply);
  }

  function playTone(noteName, delay = 0) {
    const key = noteKeys.find((item) => item.note === noteName);
    if (!key || typeof window === 'undefined') return;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = 'triangle';
    oscillator.frequency.value = key.hz;
    gain.gain.setValueAtTime(0.0001, context.currentTime + delay);
    gain.gain.exponentialRampToValueAtTime(0.18, context.currentTime + delay + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + delay + 0.28);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(context.currentTime + delay);
    oscillator.stop(context.currentTime + delay + 0.32);
  }

  function pressNote(note) {
    playTone(note);
    setPlayedNotes((prev) => [...prev, note].slice(-64));
  }

  function loadPhrase(name) {
    const notes = phraseBook[name];
    setPlayedNotes(notes);
    setProgramResult(runBrainfuck(notesToProgram(notes)));
  }

  function playPhrase() {
    playedNotes.forEach((note, idx) => playTone(note, idx * 0.18));
  }

  function runMusicProgram() {
    const result = runBrainfuck(compiledMusicProgram);
    setProgramResult(result);
    setLog((prev) => [{
      stamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      label: 'Music Keyboard',
      command: compiledMusicProgram || '(empty)',
      result: result.ok ? `output ${result.output.join(',') || result.tape0}` : result.message,
    }, ...prev].slice(0, 6));
  }

  return (
    <div className="site-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="AetherDesk home"><span>AD</span>AetherDesk</a>
        <nav>
          <a href="#station">Station</a>
          <a href="#systems">Systems</a>
          <a href="#training">Training</a>
          <a href="#music-keyboard">Music</a>
          <a href="#offers">Use/Buy</a>
          <a href="#benchmark">Benchmark</a>
          <a href="payments.html">Pricing</a>
        </nav>
        <button className="pilot" onClick={() => setPollyOpen(true)}>Talk to Polly</button>
      </header>

      <main id="top">
        <section className="hero-stage">
          <div className="street-glow" />
          <div className="hero-copy">
            <p className="system-line">SCBE-AETHERMOORE / IN-WORLD WORKSTATION</p>
            <h1>A governed AI computer.<br />Use it, prove it,<br />then ship.</h1>
            <p className="lede">AetherDesk gives AI a bounded desktop: browser, shell, writer, compiler, training room, and proof drawer. The pudding is the process: run the thing, keep the receipt.</p>
            <div className="hero-actions">
              <a className="primary" href="#station">Try the live desk</a>
              <button onClick={runRoute}>Boot selected system</button>
              <a href="#offers">See offers</a>
            </div>
          </div>

          <div className="desk-scene" id="station">
            <div className="monitor-frame">
              <div className="monitor-glass">
                <div className="screen-top">
                  <span className="dot red" /><span className="dot amber" /><span className="dot green" />
                  <b>AETHERDESK OS</b>
                  <span>{booted ? 'ONLINE' : 'STANDBY'}</span>
                </div>
                <div className="desktop-grid">
                  <aside className="dock" aria-label="AetherDesk app dock">
                    {apps.map((app) => (
                      <button key={app.id} className={activeAppId === app.id ? 'active' : ''} onClick={() => setActiveAppId(app.id)}>
                        <b>{app.name}</b><span>{app.sub}</span>
                      </button>
                    ))}
                  </aside>
                  <section className="terminal-window live-pc-window">
                    <div className="window-title"><span>{activeApp.name}</span><b>LIVE PC</b></div>
                    {renderDeskApp()}
                  </section>
                  <section className="proof-window">
                    <div className="window-title"><span>Proof drawer</span><b>linked</b></div>
                    <p>{active.caution}</p>
                    <a href={active.link}>Open source note</a>
                    <code>{active.receipt}</code>
                  </section>
                </div>
              </div>
            </div>
            <div className="desk-media" aria-label="AetherDesk visual references">
              <img src="./images/hero-art.jpg" alt="Machine Crystal artifact on a desk" />
              <img src="./images/blog-2.jpg" alt="Statue garden used as multi-agent governance visual" />
              <img src="./images/blog-6.jpg" alt="Notebook used as training and provenance visual" />
            </div>
            <div className="keyboard" />
          </div>
        </section>

        <section className="conversion-section" id="offers">
          <div className="section-head split">
            <div>
              <p className="system-line">USE / BUY / BOOK</p>
              <h2>Pick the outcome before the lore.</h2>
            </div>
            <p className="section-note">The page now leads with actions: try the desk, open the proof workbench, or book a paid pilot. The deeper systems stay underneath as evidence.</p>
          </div>
          <div className="offer-grid">
            {offerCards.map((offer) => (
              <a className="offer-card" href={offer.href} key={offer.title}>
                <span>{offer.price}</span>
                <h3>{offer.title}</h3>
                <p>{offer.body}</p>
                <b>{offer.action}</b>
              </a>
            ))}
          </div>
          <div className="pudding-strip">
            {puddingSteps.map(([title, body]) => (
              <div key={title}>
                <b>{title}</b>
                <span>{body}</span>
              </div>
            ))}
          </div>
          <div className="knife-proof-card">
            <div>
              <p className="system-line">KNIFE TEST</p>
              <h3>Small model as handle. Verifier as blade.</h3>
              <p>The chemistry adapter did not sharpen the 0.5B model on this gate. That is the point: AetherDesk makes weak AI usable by wrapping proposals in executable checks, refusal rails, and receipts.</p>
            </div>
            <div className="knife-metrics mono">
              {knifeProof.map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <b>{value}</b>
                </div>
              ))}
            </div>
            <p className="boundary">Boundary: n=10 and adapter-format caveat. This proves this gate saw no lift, not that the adapter learned nothing.</p>
          </div>
        </section>

        <section className="systems-section" id="systems">
          <div className="section-head">
            <p className="system-line">REAL REPO SYSTEMS, SURFACED AS PRODUCT</p>
            <h2>The desktop has working rooms, not empty buttons.</h2>
          </div>
          <div className="system-layout">
            <div className="system-grid">
              {systems.map((system) => (
                <button
                  key={system.id}
                  className={`system-card ${activeId === system.id ? 'active' : ''} ${system.color}`}
                  onClick={() => setActiveId(system.id)}
                >
                  <span>{system.status}</span>
                  <h3>{system.label}</h3>
                  <p>{system.short}</p>
                </button>
              ))}
            </div>

            <div className="crystal-panel">
              <div className="crystal-head">
                <div>
                  <p className="system-line">MACHINE CRYSTAL VIEWPORT</p>
                  <h3>Faces route operations.</h3>
                </div>
                <span className="mono">face:{face}</span>
              </div>
              <div className="crystal-body">
                <div className={`polyhedron f${face}`} aria-hidden="true">
                  {[0,1,2,3,4,5,6,7].map((n) => <i key={n} />)}
                </div>
                <div className="face-grid">
                  {['>','<','+','-','.',',','[',']'].map((op, idx) => (
                    <button key={op} onClick={() => setFace(idx)} className={face === idx ? 'selected' : ''}>
                      <b>{op}</b><span>{idx.toString(2).padStart(3, '0')}</span>
                    </button>
                  ))}
                </div>
              </div>
              <p className="boundary">Boundary: this is a visual controller over verified artifacts, not a browser-side compiler runtime.</p>
            </div>
          </div>
        </section>

        <section className="training-section" id="training">
          <div className="section-head split">
            <div>
              <p className="system-line">TRAINING ROOM</p>
              <h2>Boot.dev energy, but for AI operators and small models.</h2>
            </div>
            <p className="section-note">A mission board can teach humans and small LLMs how to use services, scripts, terminals, browsers, Colab, HF, and validation gates. The point is not lore. The point is repeatable computer use.</p>
          </div>
          <div className="mission-grid">
            {missions.map((mission, idx) => (
              <a className="mission-card" href={mission.link} key={mission.title}>
                <span className="mono">mission {idx + 1}</span>
                <h3>{mission.title}</h3>
                <p>{mission.body}</p>
                <b>open guide</b>
              </a>
            ))}
          </div>
        </section>

        <section className="instrument-section" id="instrument-computer">
          <div className="instrument-copy">
            <p className="system-line">INSTRUMENT COMPUTER</p>
            <h2>Any instrument can become the keyboard.</h2>
            <p className="section-note">The honest theorem is simple: the instrument supplies distinguishable notes in time. The verified Machine Crystal core supplies memory, loops, and execution. A smaller instrument alphabet just makes the song longer.</p>
            <div className="hero-actions">
              <button onClick={() => setActiveId('instrument-computer')}>Load guitar tab lane</button>
              <a href="specs/MACHINE_CRYSTAL_GEOMETRIC_TURING_OBJECT_2026-06-27.md">Open Turing object spec</a>
            </div>
          </div>
          <div className="instrument-console">
            <div className="window-title"><span>world-instrument compiler</span><b>honest reduction</b></div>
            <div className="instrument-grid mono">
              {instrumentExamples.map(([name, alphabet, encoding, result]) => (
                <div key={name}>
                  <b>{name}</b>
                  <span>{alphabet}</span>
                  <span>{encoding}</span>
                  <strong>result {result}</strong>
                </div>
              ))}
            </div>
            <div className="package-receipt-grid">
              {packageReceipts.map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <b>{value}</b>
                </div>
              ))}
            </div>
            <div className="audio-reel">
              <div>
                <span className="system-line">HOLOPHONOR REEL</span>
                <p>Generated audio is included as a playable receipt. The browser can play it; the repo CLI remains the executable source.</p>
              </div>
              <audio controls preload="metadata" src={holophonorTrack}>
                Your browser does not support the audio element.
              </audio>
            </div>
            <a className="receipt-link inline-link" href="research/INSTRUMENT_COMPUTER_README_2026-06-27.md">Open consolidated package README</a>
            <p className="boundary">Boundary: Turing-completeness is by reduction to Brainfuck on the verified core. The instrument is the input alphabet, not the memory machine.</p>
          </div>
        </section>

        <section className="music-lab-section" id="music-keyboard">
          <div className="section-head split">
            <div>
              <p className="system-line">PLAYABLE MUSIC COMPILER</p>
              <h2>Play notes. Hear sound. Build a program.</h2>
            </div>
            <p className="section-note">This first version uses browser-native Web Audio. Each key appends a note, each note maps to one Brainfuck op, and the runner executes the compiled program in the page.</p>
          </div>
          <div className="music-lab">
            <div className="piano-panel">
              <div className="piano-keys" aria-label="Playable program keyboard">
                {noteKeys.map((key) => (
                  <button key={key.note} onClick={() => pressNote(key.note)}>
                    <b>{key.note}</b>
                    <span>{key.op}</span>
                    <small>{key.role}</small>
                  </button>
                ))}
              </div>
              <div className="phrase-actions">
                <button onClick={() => loadPhrase('count4')}>load count-to-4</button>
                <button onClick={() => loadPhrase('add23')}>load add 2+3</button>
                <button onClick={() => loadPhrase('double3')}>load double 3</button>
                <button onClick={playPhrase}>play notes</button>
                <button onClick={runMusicProgram}>compile and run</button>
                <button onClick={() => { setPlayedNotes([]); setProgramResult(runBrainfuck('')); }}>clear</button>
              </div>
            </div>
            <div className="program-panel mono">
              <div className="window-title"><span>note tape -&gt; program</span><b>{programResult.ok ? 'PASS' : 'CHECK'}</b></div>
              <p><span>notes</span>{playedNotes.join(' ') || '(empty)'}</p>
              <p><span>program</span>{compiledMusicProgram || '(empty)'}</p>
              <p><span>result</span>{programResult.ok ? `${programResult.message}; tape0=${programResult.tape0}; output=[${programResult.output.join(',')}]` : programResult.message}</p>
              <p><span>boundary</span>Sound is browser-native. Production notation could later use Tone.js, abcjs, VexFlow, music21, or Magenta.js.</p>
            </div>
          </div>
          <div className="oss-music-shelf">
            {musicResources.map(([name, license, role, href]) => (
              <a key={name} href={href} target="_blank" rel="noreferrer">
                <b>{name}</b>
                <span>{license}</span>
                <p>{role}</p>
              </a>
            ))}
          </div>
        </section>

        <section className="live-coding-section" id="live-coding">
          <div className="section-head split">
            <div>
              <p className="system-line">LIVE CODING BRIDGE</p>
              <h2>Do not claim novelty. Claim the verified adapter.</h2>
            </div>
            <p className="section-note">Music-as-executable-code already exists. AetherDesk's defensible move is narrower: physical instrument input plus verified op-core plus Haskell emission, then a TidalCycles adapter.</p>
          </div>
          <div className="live-coding-grid">
            <div className="tidal-console mono">
              <div className="window-title"><span>target emitter sketch</span><b>adapter target</b></div>
              <p><span>op-bytes</span>0x00 0x02 0x0b</p>
              <p><span>haskell</span>let (b:a:t) = s in let s = (a + b) : t</p>
              <p><span>tidal</span>d1 $ sound "bd cp hh" # n "0 2 11"</p>
              <p><span>boundary</span>Haskell face is verified; Tidal execution still needs its own receipt.</p>
            </div>
            <div className="bridge-list">
              {liveCodingBridge.map(([title, body]) => (
                <div key={title}>
                  <b>{title}</b>
                  <p>{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="benchmark-section" id="benchmark">
          <div className="section-head split">
            <div>
              <p className="system-line">OUTCOME COMPUTATION BENCHMARK</p>
              <h2>Compare by what a system can actually cause.</h2>
            </div>
            <a className="receipt-link" href="research/OUTCOME_COMPUTATION_SYSTEMS_BENCHMARK_2026-06-27.md">Read full benchmark</a>
          </div>
          <div className="benchmark-table">
            {benchmarkRows.map(([name, strength, risk, use]) => (
              <div className="bench-row" key={name}>
                <b>{name}</b>
                <span>{strength}</span>
                <span>{risk}</span>
                <span>{use}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="log-section">
          <div className="log-card">
            <div>
              <p className="system-line">SESSION RECEIPT</p>
              <h2>Recent routes</h2>
            </div>
            <div className="run-log mono">
              {log.length === 0 ? <p>No browser-side route run yet. Pick a tile and press run route.</p> : log.map((item, idx) => (
                <p key={`${item.stamp}-${idx}`}><span>{item.stamp}</span> {item.label}: {item.result}</p>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer>
        <span>AetherDesk is a governed workbench surface for SCBE-AETHERMOORE.</span>
        <nav><a href="llms.txt">llms.txt</a><a href="privacy.html">privacy</a><a href="terms.html">terms</a><a href="support.html">support</a></nav>
      </footer>

      <button className={`polly-launcher ${pollyOpen ? 'hidden' : ''}`} onClick={() => setPollyOpen(true)}>
        Polly
      </button>
      <aside className={`polly-sidebar ${pollyOpen ? 'open' : ''}`} aria-label="Polly local assistant">
        <div className="polly-head">
          <div>
            <span className="system-line">POLLY LOCAL COPILOT</span>
            <h3>Talk to the site.</h3>
          </div>
          <button onClick={() => setPollyOpen(false)} aria-label="Close Polly">x</button>
        </div>
        <div className="polly-model-row" aria-label="Polly model mode">
          {pollyModes.map(([id, label]) => (
            <button key={id} className={pollyMode === id ? 'active' : ''} onClick={() => setPollyMode(id)}>
              {label}
            </button>
          ))}
        </div>
        <div className="polly-state mono">
          <p><span>active</span>{active.label}</p>
          <p><span>program</span>{compiledMusicProgram || '(empty)'}</p>
          <p><span>result</span>{programResult.ok ? `tape0 ${programResult.tape0}` : programResult.message}</p>
        </div>
        <div className="polly-messages" aria-live="polite">
          {pollyMessages.map((message, idx) => (
            <div key={`${message.role}-${idx}`} className={`polly-bubble ${message.role}`}>
              <span>{message.role === 'assistant' ? 'Polly' : 'You'}</span>
              <p>{message.text}</p>
              {message.role === 'assistant' ? <button onClick={() => speakPolly(message.text)}>speak</button> : null}
            </div>
          ))}
        </div>
        <div className="polly-quick">
          {pollyQuickPrompts.map((prompt) => (
            <button key={prompt} onClick={() => sendPolly(prompt)}>{prompt}</button>
          ))}
        </div>
        <form className="polly-compose" onSubmit={(event) => { event.preventDefault(); sendPolly(); }}>
          <textarea value={pollyInput} onChange={(event) => setPollyInput(event.target.value)} placeholder="Ask Polly about this page..." />
          <button type="submit">send</button>
        </form>
        <p className="polly-boundary">Local mode: no token, no paid model call. Polly answers from page state and uses browser speech when available.</p>
      </aside>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
