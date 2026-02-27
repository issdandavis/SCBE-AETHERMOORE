/**
 * Runtime environment validation for gateway authorization service.
 *
 * Fail-closed by design: missing governance inputs throw at startup.
 */

export interface GatewayEnv {
  readonly nodeEnv: string;
  readonly port: number;
  readonly governancePolicyId: string;
  readonly governanceIssuer: string;
  readonly governanceToken: string;
}

const REQUIRED_GOVERNANCE_ENV = [
  'GOVERNANCE_POLICY_ID',
  'GOVERNANCE_ISSUER',
  'GOVERNANCE_TOKEN',
] as const;

function toPort(rawPort: string | undefined): number {
  if (!rawPort) return 8081;
  const parsed = Number.parseInt(rawPort, 10);
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 65535) {
    throw new Error('PORT must be a valid integer between 1 and 65535');
  }
  return parsed;
}

export function redactValue(value: string): string {
  if (value.length <= 4) return '****';
  return `${value.slice(0, 2)}***${value.slice(-2)}`;
}

export function validateGatewayEnv(env: NodeJS.ProcessEnv): GatewayEnv {
  const missing = REQUIRED_GOVERNANCE_ENV.filter((key) => {
    const value = env[key];
    return value === undefined || value.trim() === '';
  });

  if (missing.length > 0) {
    throw new Error(
      `Missing required governance env vars: ${missing.join(', ')}. Startup aborted (fail-closed).`
    );
  }

  return {
    nodeEnv: env.NODE_ENV ?? 'development',
    port: toPort(env.PORT),
    governancePolicyId: env.GOVERNANCE_POLICY_ID as string,
    governanceIssuer: env.GOVERNANCE_ISSUER as string,
    governanceToken: env.GOVERNANCE_TOKEN as string,
  };
}

export function redactDiagnostics(config: GatewayEnv): Record<string, string | number> {
  return {
    nodeEnv: config.nodeEnv,
    port: config.port,
    governancePolicyId: config.governancePolicyId,
    governanceIssuer: config.governanceIssuer,
    governanceToken: redactValue(config.governanceToken),
  };
}
