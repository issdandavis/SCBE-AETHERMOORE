import { ChatWindow } from './windows/ChatWindow';

export function App() {
    return (
        <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
            <header style={{ padding: '8px 16px', borderBottom: '1px solid #ccc', fontFamily: 'monospace' }}>
                Aether Desktop — Phase 0
            </header>
            <main style={{ flex: 1, overflow: 'hidden' }}>
                <ChatWindow />
            </main>
        </div>
    );
}
