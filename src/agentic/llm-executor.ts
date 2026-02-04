/**
 * LLM Executor - Real AI provider integration
 *
 * @module agentic/llm-executor
 *
 * Supports:
 * - OpenAI (gpt-4o, gpt-4-turbo)
 * - Anthropic (claude-3-opus, claude-3-sonnet)
 * - Local (ollama, llama.cpp)
 */

import { BuiltInAgent } from './types';

/**
 * LLM Provider configuration
 */
export interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'local';
  apiKey?: string;
  baseUrl?: string;
  model?: string;
  maxTokens?: number;
  temperature?: number;
}

/**
 * Execution result from LLM
 */
export interface ExecutionResult {
  output: string;
  confidence: number;
  tokens?: number;
  model?: string;
  latencyMs?: number;
}

/**
 * Create an LLM executor for the agentic platform
 */
export function createLLMExecutor(config: LLMConfig) {
  return async (
    agent: BuiltInAgent,
    action: string,
    context: string
  ): Promise<ExecutionResult> => {
    const startTime = Date.now();

    const systemPrompt = agent.systemPrompt;
    const userPrompt = `Action: ${action}\n\nContext:\n${context}`;

    let result: ExecutionResult;

    switch (config.provider) {
      case 'openai':
        result = await callOpenAI(config, systemPrompt, userPrompt);
        break;
      case 'anthropic':
        result = await callAnthropic(config, systemPrompt, userPrompt);
        break;
      case 'local':
        result = await callLocal(config, systemPrompt, userPrompt);
        break;
      default:
        throw new Error(`Unknown provider: ${config.provider}`);
    }

    result.latencyMs = Date.now() - startTime;
    return result;
  };
}

/**
 * OpenAI API call
 */
async function callOpenAI(
  config: LLMConfig,
  systemPrompt: string,
  userPrompt: string
): Promise<ExecutionResult> {
  const apiKey = config.apiKey || process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error('OPENAI_API_KEY not set');

  const model = config.model || 'gpt-4o';
  const baseUrl = config.baseUrl || 'https://api.openai.com/v1';

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      max_tokens: config.maxTokens || 4096,
      temperature: config.temperature ?? 0.7,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI API error: ${error}`);
  }

  const data = await response.json();
  const choice = data.choices?.[0];

  return {
    output: choice?.message?.content || '',
    confidence: 0.9,
    tokens: data.usage?.total_tokens,
    model,
  };
}

/**
 * Anthropic API call
 */
async function callAnthropic(
  config: LLMConfig,
  systemPrompt: string,
  userPrompt: string
): Promise<ExecutionResult> {
  const apiKey = config.apiKey || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error('ANTHROPIC_API_KEY not set');

  const model = config.model || 'claude-sonnet-4-20250514';
  const baseUrl = config.baseUrl || 'https://api.anthropic.com/v1';

  const response = await fetch(`${baseUrl}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
      max_tokens: config.maxTokens || 4096,
      temperature: config.temperature ?? 0.7,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Anthropic API error: ${error}`);
  }

  const data = await response.json();
  const content = data.content?.[0];

  return {
    output: content?.text || '',
    confidence: 0.92,
    tokens: data.usage?.input_tokens + data.usage?.output_tokens,
    model,
  };
}

/**
 * Local LLM call (Ollama-compatible)
 */
async function callLocal(
  config: LLMConfig,
  systemPrompt: string,
  userPrompt: string
): Promise<ExecutionResult> {
  const baseUrl = config.baseUrl || 'http://localhost:11434';
  const model = config.model || 'llama3';

  const response = await fetch(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      stream: false,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Local LLM error: ${error}`);
  }

  const data = await response.json();

  return {
    output: data.message?.content || '',
    confidence: 0.8,
    tokens: data.eval_count,
    model,
  };
}

/**
 * Quick setup helpers
 */
export const Executors = {
  openai: (apiKey?: string) =>
    createLLMExecutor({ provider: 'openai', apiKey }),

  anthropic: (apiKey?: string) =>
    createLLMExecutor({ provider: 'anthropic', apiKey }),

  claude: (apiKey?: string) =>
    createLLMExecutor({
      provider: 'anthropic',
      apiKey,
      model: 'claude-sonnet-4-20250514',
    }),

  gpt4: (apiKey?: string) =>
    createLLMExecutor({ provider: 'openai', apiKey, model: 'gpt-4o' }),

  local: (model: string = 'llama3', baseUrl?: string) =>
    createLLMExecutor({ provider: 'local', model, baseUrl }),

  ollama: (model: string = 'llama3') =>
    createLLMExecutor({
      provider: 'local',
      model,
      baseUrl: 'http://localhost:11434',
    }),
};
