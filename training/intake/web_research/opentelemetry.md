# OpenTelemetry

OpenTelemetry (OTel) is a vendor-neutral open source observability framework for instrumenting, generating, collecting, and exporting telemetry data. It is an industry standard supported by over 90 observability vendors with broad organizational adoption. OTel provides APIs and SDKs across C++, .NET, Erlang/Elixir, Go, Java, JavaScript, PHP, Python, Ruby, Rust, Swift.

## Three Signal Types

### Traces
Distributed tracing captures the complete journey of requests through systems. A trace represents a single request flowing through multiple services. Each trace consists of spans — individual units of work within a service. Spans contain: operation name, start/end timestamps, attributes (key-value metadata), status, parent span ID (for causality), and links to related traces. Context propagation carries trace IDs across service boundaries using W3C TraceContext or B3 headers.

### Metrics
Quantitative measurements of system performance over time. Instrument types: Counter (monotonically increasing values like request count), UpDownCounter (values that increase and decrease like active connections), Histogram (distribution of values like response latency), Gauge (point-in-time values like CPU usage). Metrics support aggregation, filtering, and export to time-series databases. Exemplars link individual metric measurements to trace spans for correlation.

### Logs
Structured and unstructured event records documenting system state. OTel logs integrate with existing logging frameworks (log4j, Python logging, slog). Log records contain: timestamp, severity level, body (message), attributes, trace/span context. The Logs Bridge API connects existing log systems to OTel without requiring full migration.

## Additional Signals

Baggage: context data propagated across service boundaries (key-value pairs riding along with trace context). Profiles: detailed runtime behavior analysis (CPU, memory, allocation profiling).

## Architecture

### Instrumentation
Three approaches: zero-code automatic instrumentation (agent-based, no code changes), code-based manual instrumentation (explicit API calls), pre-built instrumentation libraries (middleware, HTTP clients, database drivers). Best practice: start with automatic, add manual instrumentation for business-critical paths.

### Collector
Vendor-agnostic intermediary that receives, processes, and exports telemetry data. Pipeline stages: Receivers (accept data via OTLP, Jaeger, Prometheus, etc.), Processors (batch, filter, transform, sample), Exporters (send to backends like Jaeger, Prometheus, commercial APM). Deployment patterns: Agent (sidecar alongside application), Gateway (centralized collection point). The collector decouples instrumentation from backend choice, preventing vendor lock-in.

### OTLP (OpenTelemetry Protocol)
Native wire protocol for transmitting telemetry data. Supports gRPC and HTTP/protobuf transports. Defines standard encoding for traces, metrics, and logs. Increasingly supported directly by observability backends.

## Semantic Conventions
Standardized attribute names ensuring consistent data interpretation across services and languages. Examples: http.request.method, http.response.status_code, db.system, db.statement, server.address, server.port. Enables cross-service correlation without custom mapping.
