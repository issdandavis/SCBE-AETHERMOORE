import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { execPlan, executePipelinePlan, type GeoSealPlan } from '../src/pipeline.js';
import * as processRunner from '../src/process-runner.js';
import { startAgentBusServer, type AgentBusServerHandle } from '../src/index.js';
import { enqueueEvent, getEventStatus, processOneEvent } from '../src/queue.js';
import {
  CapabilityAuthority,
  DockerSandboxExecutor,
  FileReceiptJournal,
  FileReplayStore,
  TOPOLOGY_EVIDENCE_SCHEMA,
  digestJson,
  executeAuthorizedPlan,
  issueAndExecutePlan,
  sha256Hex,
  type ExecutorRequest,
  type ExecutorResult,
  type IsolatedExecutor,
  type SecureExecutionContext,
} from '../src/secure-execution.js';

const roots: string[] = [];
const servers: AgentBusServerHandle[] = [];
const topologyPolicy = {
  profile: 'TS_PIPELINE14' as const,
  evaluatorSha256: sha256Hex('test-evaluator'),
  representationsProfile: 'byte-trit-stista-multisign-v1',
};

afterEach(async () => {
  await Promise.all(servers.splice(0).map((server) => server.close()));
  vi.restoreAllMocks();
  for (const root of roots.splice(0)) fs.rmSync(root, { recursive: true, force: true });
});

function temporaryRoot(): string {
  const container = fs.mkdtempSync(path.join(os.tmpdir(), 'scbe-capability-'));
  roots.push(container);
  const workspace = path.join(container, 'workspace');
  fs.mkdirSync(workspace);
  return workspace;
}

function plan(): GeoSealPlan {
  const intent = 'verify the workspace';
  const toolClass = 'execute_tests';
  const template = 'node -e "process.stdout.write(\'ok\')"';
  return {
    schema_version: 'scbe_command_plan_v1',
    intent: { text: intent, permission_mode: 'observe', preferred_language: 'typescript' },
    tool: {
      class: toolClass,
      contract: { tool: toolClass, risk: 'low', approval: 'auto' },
    },
    policy: { ok: true, decision: 'ALLOW', reason: 'test policy' },
    command: { key: 'test', template, runnable: true },
    hashes: {
      intent_sha256: sha256Hex(intent),
      tool_sha256: sha256Hex(toolClass),
      command_sha256: sha256Hex(template),
      plan_sha256: sha256Hex('legacy-compiler-plan'),
    },
  };
}

class RecordingExecutor implements IsolatedExecutor {
  readonly kind = 'docker' as const;
  calls: ExecutorRequest[] = [];
  result: ExecutorResult = {
    isolation: 'docker',
    ok: true,
    exitCode: 0,
    stdout: 'ok',
    stderr: '',
  };

  async execute(request: ExecutorRequest): Promise<ExecutorResult> {
    this.calls.push(request);
    return this.result;
  }
}

function fixture(root = temporaryRoot(), nowMs?: number) {
  const key = Buffer.alloc(32, 0x5a);
  const authority = new CapabilityAuthority({
    issuer: 'scbe-local-authority',
    keyId: 'local-test-key',
    key,
    maxTtlMs: 60_000,
    topologyPolicy,
  });
  const executor = new RecordingExecutor();
  const context: SecureExecutionContext = {
    authority,
    replayStore: new FileReplayStore(path.join(path.dirname(root), 'control', 'replay')),
    receiptJournal: new FileReceiptJournal({
      root: path.join(path.dirname(root), 'control', 'receipts'),
      keyId: 'local-test-key',
      key: authority.receiptKey(),
    }),
    executor,
    expectation: {
      subject: 'agent:test',
      audience: 'scbe-agent-bus',
      workspace: root,
      ...(nowMs === undefined ? {} : { nowMs }),
    },
  };
  return { root, authority, executor, context };
}

function argv(): string[] {
  return ['node', '-e', "process.stdout.write('ok')"];
}

function topology(p: GeoSealPlan, nowMs = Date.now()) {
  return {
    schema_version: TOPOLOGY_EVIDENCE_SCHEMA,
    profile: 'TS_PIPELINE14',
    decision: 'ALLOW' as const,
    evaluated_at: new Date(nowMs).toISOString(),
    expires_at: new Date(nowMs + 60_000).toISOString(),
    plan_sha256: digestJson(p),
    evaluator_sha256: sha256Hex('test-evaluator'),
    risk_receipt_sha256: sha256Hex('test-risk-receipt'),
    representations: {
      profile: 'byte-trit-stista-multisign-v1',
      bit_spine_sha256: sha256Hex('test-bit-spine'),
      trit_array_sha256: sha256Hex('test-trit-array'),
      stista_sha256: sha256Hex('test-stista'),
      multisign_sha256: sha256Hex('test-multisign'),
    },
  };
}

describe('authenticated one-use capabilities', () => {
  it('executes once and writes a signed three-record receipt chain', async () => {
    const { context, executor } = fixture();
    const p = plan();
    const result = await issueAndExecutePlan(
      p,
      argv(),
      {
        subject: 'ignored-by-trusted-context',
        audience: 'ignored-by-trusted-context',
        workspace: 'ignored-by-trusted-context',
        workspaceAccess: 'read',
        ttlMs: 30_000,
        topology: topology(p),
      },
      context
    );

    expect(result.executor.ok).toBe(true);
    expect(executor.calls).toHaveLength(1);
    const authorization = JSON.parse(fs.readFileSync(result.authorization_receipt, 'utf8'));
    const reservation = JSON.parse(fs.readFileSync(result.reservation_receipt, 'utf8'));
    const completion = JSON.parse(fs.readFileSync(result.result_receipt, 'utf8'));
    expect(context.receiptJournal.verify(authorization)).toBe(true);
    expect(context.receiptJournal.verify(reservation)).toBe(true);
    expect(context.receiptJournal.verify(completion)).toBe(true);
    expect(reservation.record.previous_receipt_sha256).toBe(digestJson(authorization));
    expect(completion.record.previous_receipt_sha256).toBe(digestJson(reservation));
    expect(completion.record.details.stdout_sha256).toBe(sha256Hex('ok'));
    expect(authorization.record.details.topology_evidence_sha256).toBe(
      digestJson(result.capability.claims.topological_authorization)
    );
    expect(authorization.record.details.topology_profile).toBe('TS_PIPELINE14');
    expect(authorization.record.details.topology_decision).toBe('ALLOW');
    expect(authorization.record.details.representation_profile).toBe(
      'byte-trit-stista-multisign-v1'
    );
  });

  it('rejects replay before a second executor call', async () => {
    const { authority, context, executor, root } = fixture();
    const p = plan();
    const token = authority.issue(p, argv(), {
      subject: 'agent:test',
      audience: 'scbe-agent-bus',
      workspace: root,
      workspaceAccess: 'read',
      isolation: 'docker',
      topology: topology(p),
    });
    await executeAuthorizedPlan(p, argv(), token, context);
    await expect(executeAuthorizedPlan(p, argv(), token, context)).rejects.toThrow(/replay/);
    expect(executor.calls).toHaveLength(1);
  });

  it('rejects plan tampering after issuance', async () => {
    const { authority, context, executor, root } = fixture();
    const original = plan();
    const token = authority.issue(original, argv(), {
      subject: 'agent:test',
      audience: 'scbe-agent-bus',
      workspace: root,
      isolation: 'docker',
      topology: topology(original),
    });
    const changed = structuredClone(original);
    changed.command.key = 'changed-after-signing';
    await expect(executeAuthorizedPlan(changed, argv(), token, context)).rejects.toThrow(/bind/);
    expect(executor.calls).toHaveLength(0);
  });

  it('rejects expired capabilities', async () => {
    const { root, authority, executor } = fixture();
    const p = plan();
    const token = authority.issue(p, argv(), {
      subject: 'agent:test',
      audience: 'scbe-agent-bus',
      workspace: root,
      isolation: 'docker',
      nowMs: 1_000,
      ttlMs: 50,
      topology: topology(p, 1_000),
    });
    const expired = fixture(root, 1_050).context;
    await expect(executeAuthorizedPlan(p, argv(), token, expired)).rejects.toThrow(
      /currently valid/
    );
    expect(executor.calls).toHaveLength(0);
  });

  it('rejects non-ALLOW, stale, and plan-mismatched topology evidence', () => {
    const { root, authority } = fixture();
    const p = plan();
    for (const decision of ['QUARANTINE', 'ESCALATE', 'DENY'] as const) {
      const evidence = topology(p);
      evidence.decision = decision;
      expect(() =>
        authority.issue(p, argv(), {
          subject: 'agent:test',
          audience: 'scbe-agent-bus',
          workspace: root,
          topology: evidence,
        })
      ).toThrow(/decision/);
    }

    expect(() =>
      authority.issue(p, argv(), {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
        nowMs: 61_000,
        topology: topology(p, 1_000),
      })
    ).toThrow(/stale/);

    const other = structuredClone(p);
    other.command.key = 'different-plan';
    expect(() =>
      authority.issue(p, argv(), {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
        topology: topology(other),
      })
    ).toThrow(/does not bind/);
  });

  it('rejects altered signatures and wrong audiences', () => {
    const { root, authority } = fixture();
    const p = plan();
    const token = authority.issue(p, argv(), {
      subject: 'agent:test',
      audience: 'scbe-agent-bus',
      workspace: root,
      isolation: 'docker',
      topology: topology(p),
    });
    const altered = structuredClone(token);
    altered.signature.value = `${altered.signature.value[0] === '0' ? '1' : '0'}${altered.signature.value.slice(1)}`;
    expect(() =>
      authority.verify(altered, p, argv(), {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
        isolation: 'docker',
      })
    ).toThrow(/signature/);
    expect(() =>
      authority.verify(token, p, argv(), {
        subject: 'agent:test',
        audience: 'other-bus',
        workspace: root,
        isolation: 'docker',
      })
    ).toThrow(/audience/);
  });

  it('does not issue authority for denied or hash-inconsistent plans', () => {
    const { root, authority } = fixture();
    const denied = plan();
    denied.policy = { ok: false, decision: 'DENY', reason: 'no' };
    expect(() =>
      authority.issue(denied, argv(), {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
        topology: topology(denied),
      })
    ).toThrow(/runnable ALLOW/);

    const corrupt = plan();
    corrupt.hashes.command_sha256 = sha256Hex('another command');
    expect(() =>
      authority.issue(corrupt, argv(), {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
        topology: topology(corrupt),
      })
    ).toThrow(/command hash/);

    const mismatched = plan();
    expect(() =>
      authority.issue(mismatched, ['node', '-e', 'process.exit(99)'], {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
        topology: topology(mismatched),
      })
    ).toThrow(/argv does not match/);
  });

  it('refuses execution when signed authorization receipts cannot be created', async () => {
    const { root, authority, executor } = fixture();
    const blockedRoot = path.join(path.dirname(root), 'receipt-is-a-file');
    fs.writeFileSync(blockedRoot, 'occupied');
    const context: SecureExecutionContext = {
      authority,
      replayStore: new FileReplayStore(path.join(path.dirname(root), 'control-closed', 'replay')),
      receiptJournal: new FileReceiptJournal({
        root: blockedRoot,
        keyId: 'local-test-key',
        key: authority.receiptKey(),
      }),
      executor,
      expectation: {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
      },
    };
    const p = plan();
    const token = authority.issue(p, argv(), {
      subject: 'agent:test',
      audience: 'scbe-agent-bus',
      workspace: root,
      isolation: 'docker',
      topology: topology(p),
    });
    await expect(executeAuthorizedPlan(p, argv(), token, context)).rejects.toThrow();
    expect(executor.calls).toHaveLength(0);
  });

  it('requires explicit strong authority and receipt keys', () => {
    expect(
      () =>
        new CapabilityAuthority({ issuer: 'x', keyId: 'k', key: Buffer.alloc(16), topologyPolicy })
    ).toThrow(/at least 32 bytes/);
    expect(
      () => new FileReceiptJournal({ root: temporaryRoot(), keyId: 'k', key: Buffer.alloc(0) })
    ).toThrow(/at least 32 bytes/);
  });
});

describe('secure Agent Bus pipeline integration', () => {
  it('blocks omitted secure context and the retired direct API without spawning', async () => {
    const spawn = vi.spyOn(processRunner, 'spawnSync');
    const p = plan();
    const result = await executePipelinePlan(p);
    expect(result.blocked).toBe(true);
    expect(result.block_reason).toMatch(/secure_execution_required/);
    expect(execPlan(p).reason).toBe('secure_execution_required');
    expect(spawn).not.toHaveBeenCalled();
  });

  it('evaluates a compiled snapshot and cannot swap commands across an await', async () => {
    const { context, executor } = fixture();
    const p = plan();
    const original = p.command.template;
    const result = await executePipelinePlan(p, {
      secureExecution: {
        context,
        grant: {
          topology: async (snapshot) => {
            p.command.template = 'node -e "process.exit(99)"';
            await Promise.resolve();
            return topology(snapshot);
          },
        },
      },
    });
    expect(result.blocked).toBe(false);
    expect(result.plan?.command.template).toBe(original);
    expect(executor.calls[0].argv).toEqual(argv());
  });

  it('refuses evaluator failure without a host fallback', async () => {
    const { context, executor } = fixture();
    const spawn = vi.spyOn(processRunner, 'spawnSync');
    const result = await executePipelinePlan(plan(), {
      secureExecution: {
        context,
        grant: {
          topology: async () => {
            throw new Error('evaluator unavailable');
          },
        },
      },
    });
    expect(result.blocked).toBe(true);
    expect(result.block_reason).toMatch(/evaluator unavailable/);
    expect(executor.calls).toHaveLength(0);
    expect(spawn).not.toHaveBeenCalled();
    expect(fs.existsSync(context.replayStore.root)).toBe(false);
  });

  it.each(['bit_spine_sha256', 'trit_array_sha256', 'stista_sha256', 'multisign_sha256'] as const)(
    'refuses missing %s before any execution or replay reservation',
    async (field) => {
      const { context, executor } = fixture();
      const p = plan();
      const evidence = topology(p);
      delete (evidence.representations as Partial<typeof evidence.representations>)[field];
      const result = await executePipelinePlan(p, {
        secureExecution: { context, grant: { topology: evidence } },
      });
      expect(result.blocked).toBe(true);
      expect(result.block_reason).toContain(field);
      expect(executor.calls).toHaveLength(0);
      expect(fs.existsSync(context.replayStore.root)).toBe(false);
    }
  );

  it.each(['profile', 'evaluator', 'representations'])(
    'refuses substituted %s identity',
    async (field) => {
      const { context, executor } = fixture();
      const p = plan();
      const evidence = topology(p);
      if (field === 'profile') evidence.profile = 'PY_REFERENCE14';
      if (field === 'evaluator') evidence.evaluator_sha256 = sha256Hex('different-evaluator');
      if (field === 'representations') evidence.representations.profile = 'different-view-map';
      const result = await executePipelinePlan(p, {
        secureExecution: { context, grant: { topology: evidence } },
      });
      expect(result.blocked).toBe(true);
      expect(result.block_reason).toMatch(/trusted policy/);
      expect(executor.calls).toHaveLength(0);
    }
  );

  it('checks the pinned profile again when verifying a signed capability', async () => {
    const { authority, context, executor, root } = fixture();
    const p = plan();
    const token = authority.issue(p, argv(), {
      subject: context.expectation.subject,
      audience: context.expectation.audience,
      workspace: root,
      topology: topology(p),
    });
    const changedAuthority = new CapabilityAuthority({
      issuer: authority.issuer,
      keyId: authority.keyId,
      key: Buffer.alloc(32, 0x5a),
      topologyPolicy: { ...topologyPolicy, profile: 'PY_REFERENCE14' },
    });
    await expect(
      executeAuthorizedPlan(p, argv(), token, {
        ...context,
        authority: changedAuthority,
      })
    ).rejects.toThrow(/trusted policy/);
    expect(executor.calls).toHaveLength(0);
  });

  it('consumes one capability only once under concurrent requests', async () => {
    const { authority, context, executor, root } = fixture();
    const p = plan();
    const token = authority.issue(p, argv(), {
      subject: context.expectation.subject,
      audience: context.expectation.audience,
      workspace: root,
      topology: topology(p),
    });
    const results = await Promise.allSettled(
      Array.from({ length: 8 }, () => executeAuthorizedPlan(p, argv(), token, context))
    );
    expect(results.filter((r) => r.status === 'fulfilled')).toHaveLength(1);
    expect(executor.calls).toHaveLength(1);
  });

  it('keeps policy and trajectory checks in front of capability execution', async () => {
    const { context, executor } = fixture();
    const p = plan();
    const result = await executePipelinePlan(p, {
      secureExecution: {
        context,
        grant: { workspaceAccess: 'read', ttlMs: 30_000, topology: topology(p) },
      },
    });
    expect(result.blocked).toBe(false);
    expect(result.result?.ok).toBe(true);
    expect(result.result?.receipt_id).toMatch(/:3$/);
    expect(result.secure_execution?.result_receipt).toBeTruthy();
    expect(executor.calls).toHaveLength(1);
  });

  it('refuses control-state storage inside a writable model workspace', async () => {
    const { root, authority, executor } = fixture();
    const context: SecureExecutionContext = {
      authority,
      replayStore: new FileReplayStore(path.join(root, 'replay')),
      receiptJournal: new FileReceiptJournal({
        root: path.join(root, 'receipts'),
        keyId: 'local-test-key',
        key: authority.receiptKey(),
      }),
      executor,
      expectation: {
        subject: 'agent:test',
        audience: 'scbe-agent-bus',
        workspace: root,
      },
    };
    const p = plan();
    const result = await executePipelinePlan(p, {
      secureExecution: { context, grant: { workspaceAccess: 'write', topology: topology(p) } },
    });
    expect(result.blocked).toBe(true);
    expect(result.block_reason).toMatch(/outside the granted workspace/);
    expect(executor.calls).toHaveLength(0);
  });
});

describe('HTTP and queue trust boundaries', () => {
  const authToken = 'test-only-http-credential-' + 'x'.repeat(32);

  function compiler(p: GeoSealPlan) {
    return vi.spyOn(processRunner, 'spawnSync').mockReturnValue({
      pid: 1,
      output: [],
      stdout: JSON.stringify(p),
      stderr: '',
      status: 0,
      signal: null,
    });
  }

  it('requires authentication to enable execution on a server', async () => {
    const { context } = fixture();
    await expect(
      startAgentBusServer({
        port: 0,
        secureExecution: {
          context,
          grant: { topology },
        },
      })
    ).rejects.toThrow(/authToken/);
  });

  it('authenticates first, rejects client options, and executes with host configuration', async () => {
    const { context, executor } = fixture();
    const p = plan();
    const spawn = compiler(p);
    const server = await startAgentBusServer({
      port: 0,
      authToken,
      geosealBin: 'trusted-test-compiler',
      secureExecution: { context, grant: { topology } },
    });
    servers.push(server);
    const request = (route: string, body: unknown, credential?: string) =>
      fetch(server.url + route, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          ...(credential ? { authorization: 'Bearer ' + credential } : {}),
        },
        body: JSON.stringify(body),
      });
    expect((await request('/v1/pipeline', { intent: p.intent.text })).status).toBe(401);
    expect((await request('/v1/pipeline', { intent: p.intent.text }, 'wrong')).status).toBe(401);
    for (const route of ['/v1/pipeline', '/v1/pipeline/compile']) {
      const denied = await request(
        route,
        {
          intent: p.intent.text,
          options: { geosealBin: 'untrusted-program', permissionMode: 'maintenance' },
        },
        authToken
      );
      expect(denied.status).toBe(400);
    }
    expect(spawn).not.toHaveBeenCalled();
    expect(executor.calls).toHaveLength(0);
    const allowed = await request('/v1/pipeline', { intent: p.intent.text }, authToken);
    expect(allowed.status).toBe(200);
    expect((await allowed.json()).result.ok).toBe(true);
    expect(spawn.mock.calls[0][0]).toBe('trusted-test-compiler');
    expect(executor.calls).toHaveLength(1);
  });

  it('keeps keys out of queue receipts and ignores serialized execution configuration', async () => {
    const { context, executor, root } = fixture();
    const p = plan();
    const spawn = compiler(p);
    const oldRoot = process.env.SCBE_BUS_QUEUE_ROOT;
    process.env.SCBE_BUS_QUEUE_ROOT = path.join(path.dirname(root), 'queue');
    const trusted = {
      authToken,
      geosealBin: 'trusted-queue-compiler',
      secureExecution: { context, grant: { topology } },
    };
    try {
      const id = enqueueEvent({ task: p.intent.text, taskType: 'pipeline' }, trusted);
      const queued = getEventStatus(id)!;
      const raw = JSON.stringify(queued);
      expect(queued.options.secureExecution).toBeUndefined();
      expect(raw).not.toContain(authToken);
      expect(raw).not.toContain('scbe-local-authority');
      const pending = path.join(process.env.SCBE_BUS_QUEUE_ROOT, 'pending');
      const file = path.join(pending, fs.readdirSync(pending)[0]);
      const altered = JSON.parse(fs.readFileSync(file, 'utf8'));
      altered.options = {
        geosealBin: 'untrusted-queue-program',
        permissionMode: 'maintenance',
        secureExecution: { context: { authority: { key: 'forged' } } },
      };
      fs.writeFileSync(file, JSON.stringify(altered));
      await processOneEvent(trusted);
      expect(getEventStatus(id)?.result?.ok).toBe(true);
      expect(executor.calls).toHaveLength(1);
      expect(spawn.mock.calls[0][0]).toBe('trusted-queue-compiler');
      expect(JSON.stringify(getEventStatus(id))).not.toContain(authToken);
    } finally {
      if (oldRoot === undefined) delete process.env.SCBE_BUS_QUEUE_ROOT;
      else process.env.SCBE_BUS_QUEUE_ROOT = oldRoot;
    }
  });
});
describe('digest-pinned Docker isolation provider', () => {
  const image = `registry.example/scbe@sha256:${'a'.repeat(64)}`;

  it('builds a shell-free, offline, least-privilege container invocation', () => {
    const root = temporaryRoot();
    const executor = new DockerSandboxExecutor({ image });
    const args = executor.buildArgs({
      argv: ['python', path.join(root, 'src', 'geoseal_cli.py'), 'status'],
      workspace: root,
      workspaceAccess: 'read',
      network: 'none',
      limits: {
        timeout_ms: 10_000,
        max_output_bytes: 1_000_000,
        memory_mb: 256,
        cpus: 1,
        pids: 64,
      },
      capabilityId: 'cap',
    });
    expect(args).toContain('none');
    expect(args).toContain('ALL');
    expect(args).toContain('no-new-privileges');
    expect(args).toContain('--read-only');
    expect(args).toContain('65532:65532');
    expect(args).toContain('never');
    expect(args).toContain(image);
    expect(args.some((item) => item.includes('readonly'))).toBe(true);
    expect(args).toContain('/workspace/src/geoseal_cli.py');
    expect(args).not.toContain('sh');
    expect(args).not.toContain('-c');
  });

  it('rejects unpinned images and host paths outside the granted workspace', () => {
    expect(() => new DockerSandboxExecutor({ image: 'scbe:latest' })).toThrow(/pinned/);
    const root = temporaryRoot();
    const executor = new DockerSandboxExecutor({ image });
    expect(() =>
      executor.buildArgs({
        argv: [path.join(path.dirname(root), 'outside.exe')],
        workspace: root,
        workspaceAccess: 'read',
        network: 'none',
        limits: {
          timeout_ms: 10_000,
          max_output_bytes: 1_000_000,
          memory_mb: 256,
          cpus: 1,
          pids: 64,
        },
        capabilityId: 'cap',
      })
    ).toThrow(/escapes workspace/);
  });

  it('fails closed when the isolation provider is unavailable', async () => {
    const executor = new DockerSandboxExecutor({
      image,
      dockerBin: path.join(temporaryRoot(), 'missing-docker'),
    });
    const result = await executor.execute({
      argv: ['python', '--version'],
      workspace: temporaryRoot(),
      workspaceAccess: 'none',
      network: 'none',
      limits: {
        timeout_ms: 1_000,
        max_output_bytes: 1_000_000,
        memory_mb: 256,
        cpus: 1,
        pids: 64,
      },
      capabilityId: 'cap',
    });
    expect(result.ok).toBe(false);
    expect(result.exitCode).not.toBe(0);
    expect(result.error).toBeTruthy();
  });
});
