/**
 * Six Tongues GeoSeal Integration
 *
 * Provides TypeScript wrapper for the Python six-tongues-geoseal CLI
 * Handles process spawning, error handling, and data streaming
 */
export interface SixTonguesConfig {
    pythonPath?: string;
    cliPath?: string;
    timeout?: number;
}
export interface EncodeOptions {
    text: string;
    context?: string;
}
export interface DecodeOptions {
    encodedText: string;
    context?: string;
}
export interface GeoSealOptions {
    data: string;
    location?: {
        lat: number;
        lon: number;
    };
    timestamp?: number;
}
export interface SixTonguesResult {
    success: boolean;
    data?: any;
    error?: string;
    stderr?: string;
}
export declare class SixTonguesIntegration {
    private config;
    private cliReady;
    constructor(config?: SixTonguesConfig);
    /**
     * Check if Python and numpy are available
     */
    checkEnvironment(): Promise<{
        python: boolean;
        numpy: boolean;
        cli: boolean;
    }>;
    /**
     * Initialize and verify the integration
     */
    initialize(): Promise<boolean>;
    /**
     * Encode text using Six Tongues tokenization
     */
    encode(options: EncodeOptions): Promise<SixTonguesResult>;
    /**
     * Decode text from Six Tongues encoding
     */
    decode(options: DecodeOptions): Promise<SixTonguesResult>;
    /**
     * Apply GeoSeal context-aware encryption
     */
    geoseal(options: GeoSealOptions): Promise<SixTonguesResult>;
    /**
     * Execute Python CLI with arguments
     */
    private runCLI;
    /**
     * Execute command and capture output
     */
    private execCommand;
}
export declare function getSixTongues(config?: SixTonguesConfig): SixTonguesIntegration;
/**
 * Convenience functions using default instance
 */
export declare function encode(text: string, context?: string): Promise<SixTonguesResult>;
export declare function decode(encodedText: string, context?: string): Promise<SixTonguesResult>;
export declare function geoseal(data: string, location?: {
    lat: number;
    lon: number;
}, timestamp?: number): Promise<SixTonguesResult>;
//# sourceMappingURL=six-tongues.d.ts.map