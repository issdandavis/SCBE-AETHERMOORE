"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.HuggingFaceClient = exports.HFApiError = void 0;
exports.setHttpTransport = setHttpTransport;
exports.resetHttpTransport = resetHttpTransport;
exports.getHuggingFaceClient = getHuggingFaceClient;
exports.resetHuggingFaceClient = resetHuggingFaceClient;
/** Default transport: native fetch */
let httpTransport = async (url, init) => {
    const res = await fetch(url, init);
    return {
        status: res.status,
        ok: res.ok,
        json: () => res.json(),
        text: () => res.text(),
    };
};
/** Inject a custom HTTP transport (for testing) */
function setHttpTransport(transport) {
    httpTransport = transport;
}
/** Reset to default fetch transport */
function resetHttpTransport() {
    httpTransport = async (url, init) => {
        const res = await fetch(url, init);
        return { status: res.status, ok: res.ok, json: () => res.json(), text: () => res.text() };
    };
}
const DEFAULT_HUB_URL = 'https://huggingface.co/api';
const DEFAULT_INFERENCE_URL = 'https://api-inference.huggingface.co';
function resolveConfig(config) {
    return {
        apiKey: config?.apiKey !== undefined ? config.apiKey : (process.env.HUGGINGFACE_API_KEY || process.env.HUGGINGFACE_TOKEN || ''),
        endpoint: config?.endpoint || process.env.HUGGINGFACE_ENDPOINT || DEFAULT_INFERENCE_URL,
        hubUrl: config?.hubUrl || DEFAULT_HUB_URL,
        timeoutMs: config?.timeoutMs ?? 30_000,
        namespace: config?.namespace || '',
    };
}
/** API error */
class HFApiError extends Error {
    status;
    endpoint;
    constructor(message, status, endpoint) {
        super(`HuggingFace API error (${status}): ${message}`);
        this.status = status;
        this.endpoint = endpoint;
        this.name = 'HFApiError';
    }
}
exports.HFApiError = HFApiError;
// ============================================================
// HUGGING FACE CLIENT
// ============================================================
/**
 * HuggingFace API client for SCBE-AETHERMOORE.
 *
 * Covers: model management, inference, datasets, model cards.
 * Injectable HTTP transport for testability.
 */
class HuggingFaceClient {
    config;
    constructor(config) {
        this.config = resolveConfig(config);
    }
    /** Check if API key is configured */
    get isConfigured() {
        return this.config.apiKey.length > 0;
    }
    /** Get authorization headers */
    authHeaders() {
        return {
            Authorization: `Bearer ${this.config.apiKey}`,
            'Content-Type': 'application/json',
        };
    }
    /** Make an authenticated API request */
    async request(baseUrl, path, method = 'GET', body) {
        if (!this.isConfigured) {
            throw new HFApiError('No API key configured', 401, path);
        }
        const url = `${baseUrl}${path}`;
        const init = {
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
    async whoami() {
        return this.request(this.config.hubUrl.replace('/api', ''), '/api/whoami-v2', 'GET');
    }
    // ── Model Management ──────────────────────────────────────
    /** List models for the authenticated user or a specific author */
    async listModels(author, limit = 20) {
        const params = new URLSearchParams({ limit: String(limit), sort: 'lastModified', direction: '-1' });
        if (author)
            params.set('author', author);
        return this.request(this.config.hubUrl, `/models?${params}`);
    }
    /** Get info about a specific model */
    async getModel(modelId) {
        return this.request(this.config.hubUrl, `/models/${modelId}`);
    }
    /** Create a new model repository */
    async createModelRepo(name, options) {
        const repoId = this.config.namespace ? `${this.config.namespace}/${name}` : name;
        return this.request(this.config.hubUrl, '/repos/create', 'POST', {
            name: repoId,
            type: 'model',
            private: options?.private ?? false,
        });
    }
    /** Delete a model repository */
    async deleteModelRepo(modelId) {
        await this.request(this.config.hubUrl, `/repos/delete`, 'DELETE', {
            name: modelId,
            type: 'model',
        });
    }
    // ── Inference API ─────────────────────────────────────────
    /** Run text generation inference */
    async textGeneration(modelId, request) {
        return this.request(this.config.endpoint, `/models/${modelId}`, 'POST', request);
    }
    /** Get embeddings (feature extraction) — feeds into 21D pipeline */
    async embeddings(modelId, request) {
        return this.request(this.config.endpoint, `/models/${modelId}`, 'POST', request);
    }
    /** Run text classification */
    async classify(modelId, inputs) {
        return this.request(this.config.endpoint, `/models/${modelId}`, 'POST', { inputs });
    }
    // ── Datasets ──────────────────────────────────────────────
    /** List datasets for an author */
    async listDatasets(author, limit = 20) {
        const params = new URLSearchParams({ limit: String(limit), sort: 'lastModified', direction: '-1' });
        if (author)
            params.set('author', author);
        return this.request(this.config.hubUrl, `/datasets?${params}`);
    }
    /** Create a dataset repository */
    async createDatasetRepo(name, options) {
        const repoId = this.config.namespace ? `${this.config.namespace}/${name}` : name;
        return this.request(this.config.hubUrl, '/repos/create', 'POST', {
            name: repoId,
            type: 'dataset',
            private: options?.private ?? false,
        });
    }
    // ── SCBE Model Card ───────────────────────────────────────
    /**
     * Generate a README.md model card with SCBE-specific metadata.
     * This is the standard HuggingFace model card format with
     * YAML frontmatter for tags, pipeline, and library.
     */
    generateModelCard(card) {
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
exports.HuggingFaceClient = HuggingFaceClient;
// ============================================================
// CONVENIENCE SINGLETON
// ============================================================
let _instance = null;
/** Get the singleton HuggingFace client */
function getHuggingFaceClient(config) {
    if (!_instance || config) {
        _instance = new HuggingFaceClient(config);
    }
    return _instance;
}
/** Reset the singleton (for testing) */
function resetHuggingFaceClient() {
    _instance = null;
}
//# sourceMappingURL=huggingface.js.map