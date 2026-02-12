type Tags = Record<string, string | number | boolean | undefined>;
export type MetricsBackend = 'stdout' | 'datadog' | 'prom' | 'otlp';
export declare const metrics: {
    timing(name: string, valueMs: number, tags?: Tags): void;
    incr(name: string, value?: number, tags?: Tags): void;
    now(): number;
};
export {};
//# sourceMappingURL=telemetry.d.ts.map