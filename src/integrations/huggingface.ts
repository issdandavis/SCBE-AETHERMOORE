/**
 * @file huggingface.ts
 * @module integrations/huggingface
 * @layer Layer 13, Layer 14
 * @component HuggingFace Platform Integration
 * @version 1.0.0
 *
 * Full HuggingFace integration for SCBE-AETHERMOORE:
 *   - Model management (list, create, delete repos)
 *   - Inference API (text generation, embeddings, classification)
 *   - Dataset operations (list, upload)
 *   - Model card generation (SCBE-specific metadata)
 *
 * Reads credentials from process.env:
 *   HUGGINGFACE_API_KEY / HUGGINGFACE_TOKEN
 *   HUGGINGFACE_ENDPOINT (default: https://api-inference.huggingface.co)
 *
 * Design: Injectable HTTP transport for testability. In production,
 * uses native fetch(). In tests, swap in a mock via setHttpTransport().
 */

// ============================================================
// HTTP TRANSPORT (injectable for testing)
// ============================================================

/** Minimal HTTP response shape */
export interface HFResponse {
  status: number;
  ok: boolean;
  json(): Promise<unknown>;
  text(): Promise<string>;
}

/** HTTP transport function signature */
export type HttpTransport = (
  url: string,
  init: {
    method: string;
    headers: Record<string, string>;
    body?: string;
  }
) => Promise<HFResponse>;

/** Default transport: native fetch */
let httpTransport: HttpTransport = async (url, init) => {
  const res = await fetch(url, init);
  return {
    status: res.status,
    ok: res.ok,
    json: () => res.json(),
    text: () => res.text(),
  };
};

/** Inject a custom HTTP transport (for testing) */
export function setHttpTransport(transport: HttpTransport): void {
  httpTransport = transport;
}

/** Reset to default fetch transport */
export function resetHttpTransport(): void {
  httpTransport = async (url, init) => {
    const res = await fetch(url, init);
    return { status: res.status, ok: res.ok, json: () => res.json(), text: () => res.text() };
  };
}

// ============================================================
// CONFIGURATION
// ============================================================

export interface HFConfig {
  /** API key (defaults to process.env.HUGGINGFACE_API_KEY) */
  apiKey?: string;
  /** Inference endpoint (defaults to process.env.HUGGINGFACE_ENDPOINT) */
  endpoint?: string;
  /** Hub API base URL */
  hubUrl?: string;
  /** Request timeout in ms */
  timeoutMs?: number;
  /** Default namespace/org for repos */
  namespace?: string;
}

const DEFAULT_HUB_URL = 'https://huggingface.co/api';
const DEFAULT_INFERENCE_URL = 'https://api-inference.huggingface.co';

function resolveConfig(config?: Partial<HFConfig>): Required<HFConfig> {
  return {
    apiKey: config?.apiKey !== undefined ? config.apiKey : (process.env.HUGGINGFACE_API_KEY || process.env.HUGGINGFACE_TOKEN || ''),
    endpoint: config?.endpoint || process.env.HUGGINGFACE_ENDPOINT || DEFAULT_INFERENCE_URL,
    hubUrl: config?.hubUrl || DEFAULT_HUB_URL,
    timeoutMs: config?.timeoutMs ?? 30_000,
    namespace: config?.namespace || '',
  };
}

// ============================================================
// TYPES
// ============================================================

/** HuggingFace model repository info */
export interface HFModelInfo {
  id: string;
  modelId: string;
  author: string;
  sha: string;
  lastModified: string;
  private: boolean;
  pipeline_tag?: string;
  tags: string[];
  downloads: number;
  likes: number;
  library_name?: string;
}

/** HuggingFace dataset info */
export interface HFDatasetInfo {
  id: string;
  author: string;
  lastModified: string;
  private: boolean;
  tags: string[];
  downloads: number;
}

/** Inference request for text generation */
export interface HFTextGenerationRequest {
  inputs: string;
  parameters?: {
    max_new_tokens?: number;
    temperature?: number;
    top_p?: number;
    top_k?: number;
    repetition_penalty?: number;
    do_sample?: boolean;
    return_full_text?: boolean;
  };
}

/** Inference result for text generation */
export interface HFTextGenerationResult {
  generated_text: string;
}

/** Inference request for embeddings (feature extraction) */
export interface HFEmbeddingRequest {
  inputs: string | string[];
  options?: {
    wait_for_model?: boolean;
    use_cache?: boolean;
  };
}

/** Classification result */
export interface HFClassificationResult {
  label: string;
  score: number;
}

/** Model card metadata for SCBE models */
export interface SCBEModelCard {
  modelName: string;
  description: string;
  pipelineTag: string;
  library: string;
  tags: string[];
  scbeVersion: string;
  patentNumber: string;
  layers: string[];
  pqcAlgorithms: string[];
  securityLevel: number;
}

/** API error */
export class HFApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly endpoint: string
  ) {
    super(`HuggingFace API error (${status}): ${message}`);
    this.name = 'HFApiError';
  }
}

// ============================================================
// HUGGING FACE CLIENT
// ============================================================

/**
 * HuggingFace API client for SCBE-AETHERMOORE.
 *
 * Covers: model management, inference, datasets, model cards.
 * Injectable HTTP transport for testability.
 */
export class HuggingFaceClient {
  private readonly config: Required<HFConfig>;

  constructor(config?: Partial<HFConfig>) {
    this.config = resolveConfig(config);
  }

  /** Check if API key is configured */
  get isConfigured(): boolean {
    return this.config.apiKey.length > 0;
  }

  /** Get authorization headers */
  private authHeaders(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.config.apiKey}`,
      'Content-Type': 'application/json',
    };
  }

  /** Make an authenticated API request */
  private async request(
    baseUrl: string,
    path: string,
    method: string = 'GET',
    body?: unknown
  ): Promise<unknown> {
    if (!this.isConfigured) {
      throw new HFApiError('No API key configured', 401, path);
    }

    const url = `${baseUrl}${path}`;
    const init: { method: string; headers: Record<string, string>; body?: string } = {
      method,
      headers: this.authHeaders(),
    };
    if (body !== undefined) {
      init.body = JSON.stringify(body);
    }

    const res = await httpTransport(url, init);

    if (!res.ok) {
      const text = await res.text().catch(() => 'unknown error');
      throw new HFApiError(text, res.status, path);
    }

    return res.json();
  }

  // ── Identity ──────────────────────────────────────────────

  /** Get authenticated user info (whoami) */
  async whoami(): Promise<{ name: string; fullname: string; email?: string; orgs?: Array<{ name: string }> }> {
    return this.request(this.config.hubUrl.replace('/api', ''), '/api/whoami-v2', 'GET') as Promise<{
      name: string; fullname: string; email?: string; orgs?: Array<{ name: string }>;
    }>;
  }

  // ── Model Management ──────────────────────────────────────

  /** List models for the authenticated user or a specific author */
  async listModels(author?: string, limit: number = 20): Promise<HFModelInfo[]> {
    const params = new URLSearchParams({ limit: String(limit), sort: 'lastModified', direction: '-1' });
    if (author) params.set('author', author);
    return this.request(this.config.hubUrl, `/models?${params}`) as Promise<HFModelInfo[]>;
  }

  /** Get info about a specific model */
  async getModel(modelId: string): Promise<HFModelInfo> {
    return this.request(this.config.hubUrl, `/models/${modelId}`) as Promise<HFModelInfo>;
  }

  /** Create a new model repository */
  async createModelRepo(
    name: string,
    options?: { private?: boolean; description?: string }
  ): Promise<{ url: string }> {
    const repoId = this.config.namespace ? `${this.config.namespace}/${name}` : name;
    return this.request(this.config.hubUrl, '/repos/create', 'POST', {
      name: repoId,
      type: 'model',
      private: options?.private ?? false,
    }) as Promise<{ url: string }>;
  }

  /** Delete a model repository */
  async deleteModelRepo(modelId: string): Promise<void> {
    await this.request(this.config.hubUrl, `/repos/delete`, 'DELETE', {
      name: modelId,
      type: 'model',
    });
  }

  // ── Inference API ─────────────────────────────────────────

  /** Run text generation inference */
  async textGeneration(
    modelId: string,
    request: HFTextGenerationRequest
  ): Promise<HFTextGenerationResult[]> {
    return this.request(
      this.config.endpoint,
      `/models/${modelId}`,
      'POST',
      request
    ) as Promise<HFTextGenerationResult[]>;
  }

  /** Get embeddings (feature extraction) — feeds into 21D pipeline */
  async embeddings(
    modelId: string,
    request: HFEmbeddingRequest
  ): Promise<number[][] | number[]> {
    return this.request(
      this.config.endpoint,
      `/models/${modelId}`,
      'POST',
      request
    ) as Promise<number[][] | number[]>;
  }

  /** Run text classification */
  async classify(
    modelId: string,
    inputs: string
  ): Promise<HFClassificationResult[][]> {
    return this.request(
      this.config.endpoint,
      `/models/${modelId}`,
      'POST',
      { inputs }
    ) as Promise<HFClassificationResult[][]>;
  }

  // ── Datasets ──────────────────────────────────────────────

  /** List datasets for an author */
  async listDatasets(author?: string, limit: number = 20): Promise<HFDatasetInfo[]> {
    const params = new URLSearchParams({ limit: String(limit), sort: 'lastModified', direction: '-1' });
    if (author) params.set('author', author);
    return this.request(this.config.hubUrl, `/datasets?${params}`) as Promise<HFDatasetInfo[]>;
  }

  /** Create a dataset repository */
  async createDatasetRepo(
    name: string,
    options?: { private?: boolean }
  ): Promise<{ url: string }> {
    const repoId = this.config.namespace ? `${this.config.namespace}/${name}` : name;
    return this.request(this.config.hubUrl, '/repos/create', 'POST', {
      name: repoId,
      type: 'dataset',
      private: options?.private ?? false,
    }) as Promise<{ url: string }>;
  }

  // ── SCBE Model Card ───────────────────────────────────────

  /**
   * Generate a README.md model card with SCBE-specific metadata.
   * This is the standard HuggingFace model card format with
   * YAML frontmatter for tags, pipeline, and library.
   */
  generateModelCard(card: SCBEModelCard): string {
    const tagLines = card.tags.map((t) => `  - ${t}`).join('\n');
    const layerLines = card.layers.map((l) => `  - ${l}`).join('\n');
    const pqcLines = card.pqcAlgorithms.map((a) => `  - ${a}`).join('\n');

    return `---
tags:
${tagLines}
  - scbe-aethermoore
  - post-quantum-cryptography
  - hyperbolic-geometry
  - ai-safety
pipeline_tag: ${card.pipelineTag}
library_name: ${card.library}
license: mit
---

# ${card.modelName}

${card.description}

## SCBE-AETHERMOORE Integration

- **Version**: ${card.scbeVersion}
- **Patent**: USPTO #${card.patentNumber}
- **Security Level**: NIST Level ${card.securityLevel}

### Pipeline Layers
${layerLines}

### Post-Quantum Cryptography
${pqcLines}

## Usage

\`\`\`typescript
import { HuggingFaceClient } from 'scbe-aethermoore/integrations';

const hf = new HuggingFaceClient();
const embeddings = await hf.embeddings('${card.modelName}', {
  inputs: 'Your input text here',
});
// Feed into 21D pipeline via projectEmbeddingToBall()
\`\`\`
`;
  }
}

// ============================================================
// CONVENIENCE SINGLETON
// ============================================================

let _instance: HuggingFaceClient | null = null;

/** Get the singleton HuggingFace client */
export function getHuggingFaceClient(config?: Partial<HFConfig>): HuggingFaceClient {
  if (!_instance || config) {
    _instance = new HuggingFaceClient(config);
  }
  return _instance;
}

/** Reset the singleton (for testing) */
export function resetHuggingFaceClient(): void {
  _instance = null;
}
