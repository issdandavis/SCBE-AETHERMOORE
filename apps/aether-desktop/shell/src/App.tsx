import { useState, useMemo } from 'react';
import { ChatWindow } from './windows/ChatWindow';
import { ToolConsole } from './windows/ToolConsole';
import { createBackendClient } from './BackendClient';
import { createToolBus } from './toolBus';

const BACKEND_URL =
  (import.meta.env['VITE_BACKEND_URL'] as string | undefined) ?? 'http://localhost:8001';
const BACKEND_API_KEY = import.meta.env['VITE_BACKEND_API_KEY'] as string | undefined;

type Tab = 'chat' | 'tools';

const TAB_BTN = (active: boolean): React.CSSProperties => ({
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  fontFamily: 'monospace',
  fontSize: 13,
  fontWeight: active ? 'bold' : 'normal',
  borderBottom: active ? '2px solid #333' : '2px solid transparent',
  padding: '2px 4px',
});

export function App() {
  const [tab, setTab] = useState<Tab>('chat');
  const client = useMemo(() => createBackendClient(BACKEND_URL, BACKEND_API_KEY), []);
  const bus = useMemo(() => createToolBus(client), [client]);

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          padding: '6px 16px',
          borderBottom: '1px solid #ccc',
          fontFamily: 'monospace',
          display: 'flex',
          gap: 16,
          alignItems: 'center',
        }}
      >
        <span style={{ fontWeight: 'bold' }}>Aether Desktop</span>
        <button style={TAB_BTN(tab === 'chat')} onClick={() => setTab('chat')}>
          Chat
        </button>
        <button style={TAB_BTN(tab === 'tools')} onClick={() => setTab('tools')}>
          Tools
        </button>
      </header>
      <main style={{ flex: 1, overflow: 'hidden' }}>
        {tab === 'chat' ? <ChatWindow /> : <ToolConsole bus={bus} />}
      </main>
    </div>
  );
}
