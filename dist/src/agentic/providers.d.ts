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
export declare function callProvider(prompt: string, options?: CallOptions): Promise<ProviderResponse>;
/**
 * Get list of available providers (those with valid API keys)
 */
export declare function getAvailableProviders(): ProviderName[];
/**
 * Get provider status for diagnostics
 */
export declare function getProviderStatus(): Record<ProviderName, {
    available: boolean;
    model: string;
}>;
/**
 * Call a specific provider (bypass priority chain)
 */
export declare function callSpecificProvider(providerName: ProviderName, prompt: string, options?: CallOptions): Promise<ProviderResponse>;
/**
 * Create a signed provider request attestation
 * Used for audit trail and trust verification
 */
export declare function createProviderAttestation(prompt: string, response: ProviderResponse, secretKey?: Buffer): {
    attestation: string;
    signature: string;
};
declare const _default: {
    callProvider: typeof callProvider;
    callSpecificProvider: typeof callSpecificProvider;
    getAvailableProviders: typeof getAvailableProviders;
    getProviderStatus: typeof getProviderStatus;
    createProviderAttestation: typeof createProviderAttestation;
};
export default _default;
//# sourceMappingURL=providers.d.ts.map