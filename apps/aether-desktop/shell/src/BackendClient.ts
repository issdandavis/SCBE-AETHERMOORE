export interface OperationRequest {
  schema_version: string;
  op: string;
  args: Record<string, unknown>;
  request_id: string;
  origin: { kind: 'app' | 'workflow' | 'agent'; id: string };
  workspace?: { id: string; root: string };
  privacy: 'local_only' | 'external_api';
  budget_cents?: number;
  dry_run?: boolean;
}

export interface OperationResult {
  request_id: string;
  ok: boolean;
  output?: Record<string, unknown>;
  error?: { code: string; message: string };
  artifacts?: { kind: string; ref: string }[];
  duration_ms: number;
}

export interface BackendClient {
  runOp(req: OperationRequest): Promise<OperationResult>;
  subscribeEvents(
    requestId: string,
    onEvent: (event: Record<string, unknown>) => void,
    onDone: (event: Record<string, unknown>) => void
  ): EventSubscription;
}

export interface EventSubscription {
  ready: Promise<void>;
  unsubscribe: () => void;
}

export function createBackendClient(baseUrl: string): BackendClient {
  const wsBase = baseUrl.replace(/^http/, 'ws');

  return {
    async runOp(req: OperationRequest): Promise<OperationResult> {
      const resp = await fetch(`${baseUrl}/v1/op`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });
      return resp.json() as Promise<OperationResult>;
    },

    subscribeEvents(requestId, onEvent, onDone) {
      const ws = new WebSocket(`${wsBase}/v1/events?request_id=${requestId}`);
      const ready = new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () =>
          reject(new Error(`WebSocket connection failed for request ${requestId}`));
      });
      ws.onmessage = (e: MessageEvent) => {
        const event = JSON.parse(e.data as string) as Record<string, unknown>;
        if (event['type'] === 'done') {
          onDone(event);
          ws.close();
        } else {
          onEvent(event);
        }
      };
      return { ready, unsubscribe: () => ws.close() };
    },
  };
}

export const SCHEMA_VERSION = 'scbe.operation.v1' as const;
