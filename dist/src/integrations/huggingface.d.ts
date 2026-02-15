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
/** Minimal HTTP response shape */
export interface HFResponse {
    status: number;
    ok: boolean;
    json(): Promise<unknown>;
    text(): Promise<string>;
}
/** HTTP transport function signature */
export type HttpTransport = (url: string, init: {
    method: string;
    headers: Record<string, string>;
    body?: string;
}) => Promise<HFResponse>;
/** Inject a custom HTTP transport (for testing) */
export declare function setHttpTransport(transport: HttpTransport): void;
/** Reset to default fetch transport */
export declare function resetHttpTransport(): void;
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
export declare class HFApiError extends Error {
    readonly status: number;
    readonly endpoint: string;
    constructor(message: string, status: number, endpoint: string);
}
/**
 * HuggingFace API client for SCBE-AETHERMOORE.
 *
 * Covers: model management, inference, datasets, model cards.
 * Injectable HTTP transport for testability.
 */
export declare class HuggingFaceClient {
    private readonly config;
    constructor(config?: Partial<HFConfig>);
    /** Check if API key is configured */
    get isConfigured(): boolean;
    /** Get authorization headers */
    private authHeaders;
    /** Make an authenticated API request */
    private request;
    /** Get authenticated user info (whoami) */
    whoami(): Promise<{
        name: string;
        fullname: string;
        email?: string;
        orgs?: Array<{
            name: string;
        }>;
    }>;
    /** List models for the authenticated user or a specific author */
    listModels(author?: string, limit?: number): Promise<HFModelInfo[]>;
    /** Get info about a specific model */
    getModel(modelId: string): Promise<HFModelInfo>;
    /** Create a new model repository */
    createModelRepo(name: string, options?: {
        private?: boolean;
        description?: string;
    }): Promise<{
        url: string;
    }>;
    /** Delete a model repository */
    deleteModelRepo(modelId: string): Promise<void>;
    /** Run text generation inference */
    textGeneration(modelId: string, request: HFTextGenerationRequest): Promise<HFTextGenerationResult[]>;
    /** Get embeddings (feature extraction) — feeds into 21D pipeline */
    embeddings(modelId: string, request: HFEmbeddingRequest): Promise<number[][] | number[]>;
    /** Run text classification */
    classify(modelId: string, inputs: string): Promise<HFClassificationResult[][]>;
    /** List datasets for an author */
    listDatasets(author?: string, limit?: number): Promise<HFDatasetInfo[]>;
    /** Create a dataset repository */
    createDatasetRepo(name: string, options?: {
        private?: boolean;
    }): Promise<{
        url: string;
    }>;
    /**
     * Generate a README.md model card with SCBE-specific metadata.
     * This is the standard HuggingFace model card format with
     * YAML frontmatter for tags, pipeline, and library.
     */
    generateModelCard(card: SCBEModelCard): string;
}
/** Get the singleton HuggingFace client */
export declare function getHuggingFaceClient(config?: Partial<HFConfig>): HuggingFaceClient;
/** Reset the singleton (for testing) */
export declare function resetHuggingFaceClient(): void;
//# sourceMappingURL=huggingface.d.ts.map