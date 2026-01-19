/**
 * Enterprise-Grade Testing Suite Configuration
 * 
 * This configuration defines thresholds, timeouts, and settings for the
 * enterprise test suite.
 */

export const TestConfig = {
  // Property-based testing
  propertyTests: {
    minIterations: 100,
    maxIterations: 1000,
    timeout: 60000, // 60 seconds per property test
  },

  // Quantum testing
  quantum: {
    maxQubits: 20, // Classical simulation limit
    targetSecurityBits: 256,
    algorithms: {
      shor: { enabled: true, maxKeySize: 4096 },
      grover: { enabled: true, maxSearchSpace: 1048576 },
    },
  },

  // AI safety testing
  aiSafety: {
    intentVerificationAccuracy: 0.999, // 99.9%
    riskThreshold: 0.8,
    consensusTimeout: 5000, // 5 seconds
    failSafeActivationTime: 100, // 100ms
  },

  // Agentic coding
  agentic: {
    vulnerabilityDetectionRate: 0.95, // 95%
    approvalTimeout: 300000, // 5 minutes
    maxCodeSize: 10000, // lines
  },

  // Compliance testing
  compliance: {
    controlCoverageTarget: 1.0, // 100%
    complianceScoreTarget: 0.98, // 98%
    standards: ['SOC2', 'ISO27001', 'FIPS140', 'CommonCriteria', 'NISTCSF', 'PCIDSS'],
  },

  // Stress testing
  stress: {
    targetThroughput: 1000000, // 1M req/s
    concurrentAttacks: 10000,
    soakTestDuration: 259200000, // 72 hours in ms
    latencyTargets: {
      p50: 5,
      p95: 10,
      p99: 20,
      p999: 50,
      p9999: 100,
    },
  },

  // Security testing
  security: {
    fuzzingIterations: 1000000000, // 1 billion
    faultInjectionCount: 1000,
    timingLeakThreshold: 0.01, // 1% variance
  },

  // Coverage targets
  coverage: {
    lines: 95,
    functions: 95,
    branches: 95,
    statements: 95,
  },

  // Test execution
  execution: {
    parallelism: 8, // Number of parallel test workers
    retries: 2,
    timeout: 30000, // 30 seconds default
    longRunningTimeout: 7200000, // 2 hours for stress tests
  },

  // Reporting
  reporting: {
    formats: ['json', 'html', 'markdown'],
    dashboardRefreshInterval: 5000, // 5 seconds
    evidenceRetentionDays: 2555, // 7 years
  },
} as const;

export type TestConfigType = typeof TestConfig;
