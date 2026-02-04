/**
 * @file providers.ts
 * @module agentic/providers
 * @layer Layer 13 (Decision Gate)
 * @component AI Provider Integration with Fallback Chain
 * @version 1.0.0
 *
 * Manages AI provider connections with:
 * - Priority-based provider selection (your keys first)
 * - Automatic fallback on failure
 * - Rate limiting and timeout handling
 * - Sacred Tongues trust verification integration
 */

import { createHmac } from 'crypto';

// ============================================================================
// Types
// ============================================================================

export type ProviderName = 'anthropic' | 'openai' | 'google' | 'mistral' | 'cohere';

export interface ProviderConfig {
  name: ProviderName;
  apiKey: string;
  model: string;
  baseUrl?: string;
  available: boolean;
}

export interface ProviderResponse {
  output: string;
  tokensUsed: number;
  provider: ProviderName;
  model: string;
  latencyMs: number;
}

export interface ProviderError {
  provider: ProviderName;
  error: string;
  retryable: boolean;
}

export interface CallOptions {
  maxTokens?: number;
  temperature?: number;
  systemPrompt?: string;
  timeout?: number;
}

// ============================================================================
// Configuration
// ============================================================================

/** Load provider priority from environment */
function getProviderPriority(): ProviderName[] {
  const priority = process.env.SCBE_PROVIDER_PRIORITY || 'anthropic,openai,google';
  return priority.split(',').map((p) => p.trim().toLowerCase() as ProviderName);
}

/** Get configuration for all providers */
function getProviderConfigs(): Map<ProviderName, ProviderConfig> {
  const configs = new Map<ProviderName, ProviderConfig>();

  // Anthropic
  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  configs.set('anthropic', {
    name: 'anthropic',
    apiKey: anthropicKey || '',
    model: process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-20250514',
    baseUrl: 'https://api.anthropic.com/v1',
    available: !!anthropicKey && !anthropicKey.includes('...'),
  });

  // OpenAI
  const openaiKey = process.env.OPENAI_API_KEY;
  configs.set('openai', {
    name: 'openai',
    apiKey: openaiKey || '',
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    baseUrl: 'https://api.openai.com/v1',
    available: !!openaiKey && !openaiKey.includes('...'),
  });

  // Google
  const googleKey = process.env.GOOGLE_API_KEY;
  configs.set('google', {
    name: 'google',
    apiKey: googleKey || '',
    model: process.env.GOOGLE_MODEL || 'gemini-2.0-flash',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    available: !!googleKey && !googleKey.includes('...'),
  });

  // Mistral
  const mistralKey = process.env.MISTRAL_API_KEY;
  configs.set('mistral', {
    name: 'mistral',
    apiKey: mistralKey || '',
    model: process.env.MISTRAL_MODEL || 'mistral-large-latest',
    baseUrl: 'https://api.mistral.ai/v1',
    available: !!mistralKey && !mistralKey.includes('...'),
  });

  // Cohere
  const cohereKey = process.env.COHERE_API_KEY;
  configs.set('cohere', {
    name: 'cohere',
    apiKey: cohereKey || '',
    model: process.env.COHERE_MODEL || 'command-r-plus',
    baseUrl: 'https://api.cohere.ai/v1',
    available: !!cohereKey && !cohereKey.includes('...'),
  });

  return configs;
}

// ============================================================================
// Provider Implementations
// ============================================================================

async function callAnthropic(
  config: ProviderConfig,
  prompt: string,
  options: CallOptions
): Promise<ProviderResponse> {
  const start = Date.now();

  const response = await fetch(`${config.baseUrl}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': config.apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: config.model,
      max_tokens: options.maxTokens || 4096,
      temperature: options.temperature ?? 0.7,
      system: options.systemPrompt,
      messages: [{ role: 'user', content: prompt }],
    }),
    signal: AbortSignal.timeout(options.timeout || 30000),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Anthropic API error: ${response.status} - ${error}`);
  }

  const data = await response.json();
  const latency = Date.now() - start;

  return {
    output: data.content[0]?.text || '',
    tokensUsed: (data.usage?.input_tokens || 0) + (data.usage?.output_tokens || 0),
    provider: 'anthropic',
    model: config.model,
    latencyMs: latency,
  };
}

async function callOpenAI(
  config: ProviderConfig,
  prompt: string,
  options: CallOptions
): Promise<ProviderResponse> {
  const start = Date.now();

  const messages: Array<{ role: string; content: string }> = [];
  if (options.systemPrompt) {
    messages.push({ role: 'system', content: options.systemPrompt });
  }
  messages.push({ role: 'user', content: prompt });

  const response = await fetch(`${config.baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      max_tokens: options.maxTokens || 4096,
      temperature: options.temperature ?? 0.7,
      messages,
    }),
    signal: AbortSignal.timeout(options.timeout || 30000),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI API error: ${response.status} - ${error}`);
  }

  const data = await response.json();
  const latency = Date.now() - start;

  return {
    output: data.choices[0]?.message?.content || '',
    tokensUsed: data.usage?.total_tokens || 0,
    provider: 'openai',
    model: config.model,
    latencyMs: latency,
  };
}

async function callGoogle(
  config: ProviderConfig,
  prompt: string,
  options: CallOptions
): Promise<ProviderResponse> {
  const start = Date.now();

  const url = `${config.baseUrl}/models/${config.model}:generateContent?key=${config.apiKey}`;

  const contents = [];
  if (options.systemPrompt) {
    contents.push({ role: 'user', parts: [{ text: options.systemPrompt }] });
    contents.push({ role: 'model', parts: [{ text: 'Understood.' }] });
  }
  contents.push({ role: 'user', parts: [{ text: prompt }] });

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents,
      generationConfig: {
        maxOutputTokens: options.maxTokens || 4096,
        temperature: options.temperature ?? 0.7,
      },
    }),
    signal: AbortSignal.timeout(options.timeout || 30000),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Google API error: ${response.status} - ${error}`);
  }

  const data = await response.json();
  const latency = Date.now() - start;

  return {
    output: data.candidates?.[0]?.content?.parts?.[0]?.text || '',
    tokensUsed: data.usageMetadata?.totalTokenCount || 0,
    provider: 'google',
    model: config.model,
    latencyMs: latency,
  };
}

async function callMistral(
  config: ProviderConfig,
  prompt: string,
  options: CallOptions
): Promise<ProviderResponse> {
  const start = Date.now();

  const messages: Array<{ role: string; content: string }> = [];
  if (options.systemPrompt) {
    messages.push({ role: 'system', content: options.systemPrompt });
  }
  messages.push({ role: 'user', content: prompt });

  const response = await fetch(`${config.baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      max_tokens: options.maxTokens || 4096,
      temperature: options.temperature ?? 0.7,
      messages,
    }),
    signal: AbortSignal.timeout(options.timeout || 30000),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Mistral API error: ${response.status} - ${error}`);
  }

  const data = await response.json();
  const latency = Date.now() - start;

  return {
    output: data.choices[0]?.message?.content || '',
    tokensUsed: data.usage?.total_tokens || 0,
    provider: 'mistral',
    model: config.model,
    latencyMs: latency,
  };
}

async function callCohere(
  config: ProviderConfig,
  prompt: string,
  options: CallOptions
): Promise<ProviderResponse> {
  const start = Date.now();

  const response = await fetch(`${config.baseUrl}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      message: prompt,
      preamble: options.systemPrompt,
      max_tokens: options.maxTokens || 4096,
      temperature: options.temperature ?? 0.7,
    }),
    signal: AbortSignal.timeout(options.timeout || 30000),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Cohere API error: ${response.status} - ${error}`);
  }

  const data = await response.json();
  const latency = Date.now() - start;

  return {
    output: data.text || '',
    tokensUsed: data.meta?.tokens?.input_tokens + data.meta?.tokens?.output_tokens || 0,
    provider: 'cohere',
    model: config.model,
    latencyMs: latency,
  };
}

// ============================================================================
// Provider Router (Main Export)
// ============================================================================

const PROVIDER_CALLERS: Record<
  ProviderName,
  (config: ProviderConfig, prompt: string, options: CallOptions) => Promise<ProviderResponse>
> = {
  anthropic: callAnthropic,
  openai: callOpenAI,
  google: callGoogle,
  mistral: callMistral,
  cohere: callCohere,
};

/**
 * Call AI provider with automatic fallback chain
 *
 * Tries providers in priority order (from SCBE_PROVIDER_PRIORITY env var).
 * Falls back to next provider on failure if SCBE_PROVIDER_FALLBACK_ENABLED=true.
 *
 * @param prompt - The prompt to send
 * @param options - Call options (maxTokens, temperature, etc.)
 * @returns Provider response with output text and metadata
 * @throws Error if all providers fail
 */
export async function callProvider(
  prompt: string,
  options: CallOptions = {}
): Promise<ProviderResponse> {
  const priority = getProviderPriority();
  const configs = getProviderConfigs();
  const fallbackEnabled = process.env.SCBE_PROVIDER_FALLBACK_ENABLED !== 'false';
  const maxRetries = parseInt(process.env.SCBE_PROVIDER_MAX_RETRIES || '2', 10);
  const timeout = parseInt(process.env.SCBE_PROVIDER_TIMEOUT_MS || '30000', 10);

  const errors: ProviderError[] = [];

  for (const providerName of priority) {
    const config = configs.get(providerName);

    if (!config?.available) {
      errors.push({
        provider: providerName,
        error: 'API key not configured',
        retryable: false,
      });
      continue;
    }

    const caller = PROVIDER_CALLERS[providerName];

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const result = await caller(config, prompt, { ...options, timeout });
        return result;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        const isRetryable = errorMsg.includes('timeout') || errorMsg.includes('rate limit');

        errors.push({
          provider: providerName,
          error: `Attempt ${attempt + 1}: ${errorMsg}`,
          retryable: isRetryable,
        });

        if (!isRetryable || attempt === maxRetries - 1) {
          break;
        }

        // Exponential backoff
        await new Promise((resolve) => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
      }
    }

    if (!fallbackEnabled) {
      break;
    }
  }

  throw new Error(
    `All providers failed:\n${errors.map((e) => `  ${e.provider}: ${e.error}`).join('\n')}`
  );
}

/**
 * Get list of available providers (those with valid API keys)
 */
export function getAvailableProviders(): ProviderName[] {
  const configs = getProviderConfigs();
  return Array.from(configs.entries())
    .filter(([_, config]) => config.available)
    .map(([name, _]) => name);
}

/**
 * Get provider status for diagnostics
 */
export function getProviderStatus(): Record<ProviderName, { available: boolean; model: string }> {
  const configs = getProviderConfigs();
  const status: Record<string, { available: boolean; model: string }> = {};

  for (const [name, config] of configs.entries()) {
    status[name] = {
      available: config.available,
      model: config.model,
    };
  }

  return status as Record<ProviderName, { available: boolean; model: string }>;
}

/**
 * Call a specific provider (bypass priority chain)
 */
export async function callSpecificProvider(
  providerName: ProviderName,
  prompt: string,
  options: CallOptions = {}
): Promise<ProviderResponse> {
  const configs = getProviderConfigs();
  const config = configs.get(providerName);

  if (!config?.available) {
    throw new Error(`Provider ${providerName} not configured or API key missing`);
  }

  const caller = PROVIDER_CALLERS[providerName];
  const timeout = parseInt(process.env.SCBE_PROVIDER_TIMEOUT_MS || '30000', 10);

  return caller(config, prompt, { ...options, timeout });
}

// ============================================================================
// Sacred Tongues Integration
// ============================================================================

/**
 * Create a signed provider request attestation
 * Used for audit trail and trust verification
 */
export function createProviderAttestation(
  prompt: string,
  response: ProviderResponse,
  secretKey?: Buffer
): { attestation: string; signature: string } {
  const attestation = JSON.stringify({
    provider: response.provider,
    model: response.model,
    promptHash: createHmac('sha256', 'scbe-prompt').update(prompt).digest('hex').slice(0, 16),
    outputHash: createHmac('sha256', 'scbe-output')
      .update(response.output)
      .digest('hex')
      .slice(0, 16),
    tokensUsed: response.tokensUsed,
    latencyMs: response.latencyMs,
    timestamp: Date.now(),
  });

  const signature = secretKey
    ? createHmac('sha256', secretKey).update(attestation).digest('hex')
    : '';

  return { attestation, signature };
}

export default {
  callProvider,
  callSpecificProvider,
  getAvailableProviders,
  getProviderStatus,
  createProviderAttestation,
};
