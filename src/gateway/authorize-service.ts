import express, { NextFunction, Request, Response } from 'express';
import { UnifiedKernel, type ProposedAction, type MemoryEvent } from '../ai_brain/unified-kernel';
import { validateGatewayEnv, redactDiagnostics } from './env';

interface AuthorizeRequest {
  agentId: string;
  actionType: string;
  stateVector: number[];
  meta?: Record<string, unknown>;
  memoryEvent?: {
    contentHash: string;
    domain: number;
    sequence: number;
    polarity: number;
    authority: number;
  };
}

function parseMemoryEvent(event: AuthorizeRequest['memoryEvent']): MemoryEvent | undefined {
  if (!event) {
    return undefined;
  }
  return {
    contentHash: event.contentHash,
    domain: event.domain,
    sequence: event.sequence,
    polarity: event.polarity,
    authority: event.authority,
  };
}

function toHttpDecision(
  kernelDecision: 'ALLOW' | 'TRANSFORM' | 'BLOCK'
): 'ALLOW' | 'QUARANTINE' | 'DENY' {
  if (kernelDecision === 'ALLOW') return 'ALLOW';
  if (kernelDecision === 'TRANSFORM') return 'QUARANTINE';
  return 'DENY';
}

function validateRequest(body: Partial<AuthorizeRequest>): string | null {
  if (!body.agentId || body.agentId.trim() === '') return 'agentId is required';
  if (!body.actionType || body.actionType.trim() === '') return 'actionType is required';
  if (!Array.isArray(body.stateVector) || body.stateVector.length === 0) {
    return 'stateVector must be a non-empty numeric array';
  }
  if (body.stateVector.some((v) => typeof v !== 'number' || Number.isNaN(v))) {
    return 'stateVector must only contain valid numbers';
  }
  return null;
}

export function createAuthorizeApp() {
  const env = validateGatewayEnv(process.env);
  const app = express();
  const kernel = new UnifiedKernel();

  app.use(express.json({ limit: '1mb' }));

  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  app.post('/authorize', (req: Request, res: Response) => {
    const validationError = validateRequest(req.body as Partial<AuthorizeRequest>);
    if (validationError) {
      res.status(400).json({ error: validationError });
      return;
    }

    const payload = req.body as AuthorizeRequest;
    const action: ProposedAction = {
      type: payload.actionType,
      stateVector: payload.stateVector,
      meta: payload.meta,
    };

    const result = kernel.processAction(
      payload.agentId,
      action,
      parseMemoryEvent(payload.memoryEvent)
    );

    res.json({
      agentId: payload.agentId,
      decision: toHttpDecision(result.decision),
      kernelDecision: result.decision,
      step: result.step,
      combinedRiskScore: result.metrics.combinedRiskScore,
      immuneState: result.state.immuneState,
      fluxState: result.state.fluxState,
      penaltyApplied: result.penaltyApplied,
      auditHash: result.auditHash,
    });
  });

  app.use((error: Error, _req: Request, res: Response, _next: NextFunction) => {
    console.error('gateway_error', { message: error.message });
    res.status(500).json({ error: 'internal_error' });
  });

  return { app, env };
}

export function startAuthorizeService(): void {
  const { app, env } = createAuthorizeApp();

  console.info('gateway_startup', redactDiagnostics(env));

  app.listen(env.port, () => {
    console.info('gateway_listening', { port: env.port, nodeEnv: env.nodeEnv });
  });
}

if (require.main === module) {
  try {
    startAuthorizeService();
  } catch (error) {
    const message = error instanceof Error ? error.message : 'unknown startup failure';
    console.error('gateway_startup_failed', { message });
    process.exit(1);
  }
}
