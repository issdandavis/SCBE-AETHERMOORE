import { useCallback, useRef, useState } from 'react';
import { createBackendClient, SCHEMA_VERSION } from '../BackendClient';
import type { OperationRequest } from '../BackendClient';

const client = createBackendClient(
    (import.meta as unknown as { env: Record<string, string> }).env?.['VITE_BACKEND_URL'] ??
        'http://localhost:8001'
);

export function ChatWindow() {
    const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
    const [input, setInput] = useState('');
    const [streaming, setStreaming] = useState('');
    const streamRef = useRef('');

    const send = useCallback(async () => {
        const text = input.trim();
        if (!text) return;

        const userMsg = { role: 'user', content: text };
        const nextMessages = [...messages, userMsg];
        setMessages(nextMessages);
        setInput('');
        streamRef.current = '';
        setStreaming('');

        const requestId = crypto.randomUUID();
        const req: OperationRequest = {
            schema_version: SCHEMA_VERSION,
            op: 'llm.chat',
            args: { messages: nextMessages, model: 'llama3' },
            request_id: requestId,
            origin: { kind: 'app', id: 'chat-window' },
            privacy: 'local_only',
        };

        client.subscribeEvents(
            requestId,
            (e) => {
                if (e['type'] === 'token' && typeof e['content'] === 'string') {
                    streamRef.current += e['content'];
                    setStreaming(streamRef.current);
                }
            },
            () => {
                setMessages((prev) => [...prev, { role: 'assistant', content: streamRef.current }]);
                streamRef.current = '';
                setStreaming('');
            }
        );

        await client.runOp(req);
    }, [input, messages]);

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 8, fontFamily: 'monospace' }}>
            <div style={{ flex: 1, overflowY: 'auto', marginBottom: 8 }}>
                {messages.map((m, i) => (
                    <div key={i} style={{ marginBottom: 4 }}>
                        <strong>{m.role}:</strong> {m.content}
                    </div>
                ))}
                {streaming && (
                    <div style={{ marginBottom: 4 }}>
                        <strong>assistant:</strong> {streaming}
                    </div>
                )}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') void send();
                    }}
                    style={{ flex: 1, padding: '4px 8px' }}
                    placeholder="Type a message and press Enter..."
                />
                <button onClick={() => void send()} style={{ padding: '4px 12px' }}>
                    Send
                </button>
            </div>
        </div>
    );
}
