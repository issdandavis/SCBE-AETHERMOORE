/**
 * Test Scheduler - Prioritizes and schedules test execution
 * 
 * Feature: enterprise-grade-testing
 * Component: Test Orchestration Engine
 * Validates: TR-7.1, TR-7.2
 */

export interface Test {
  id: string;
  name: string;
  description: string;
  requirements: string[]; // References to requirements (e.g., "AC-1.1")
  propertyNumber?: number; // References to design property
  execute: () => Promise<TestResult>;
  estimatedDuration?: number; // milliseconds
  priority?: number; // 1-10, higher = more important
  tags?: string[];
}

export interface TestSuite {
  name: string;
  category: 'quantum' | 'ai-safety' | 'agentic' | 'compliance' | 'stress' | 'security' | 'formal' | 'integration';
  tests: Test[];
  dependencies: string[]; // Suite names this depends on
  priority: number; // 1-10
  estimatedDuration: number; // milliseconds
}

export interface ExecutionPhase {
  name: string;
  tests: Test[];
  canRunInParallel: boolean;
  dependencies: string[];
}

export interface ExecutionPlan {
  phases: ExecutionPhase[];
  totalTests: number;
  estimatedDuration: number;
  parallelism: number;
}

export interface TestResult {
  testId: string;
  status: 'passed' | 'failed' | 'skipped' | 'error';
  duration: number;
  message?: string;
  evidence?: Evidence;
  metrics?: Record<string, number>;
  error?: Error;
}

export interface Evidence {
  id: string;
  type: 'log' | 'screenshot' | 'report' | 'certificate' | 'metric';
  name: string;
  content: Buffer | string;
  hash: string;
  timestamp: Date;
}

/**
 * TestScheduler - Prioritizes and schedules test execution
 * 
 * Responsibilities:
 * - Analyze test dependencies
 * - Prioritize tests based on criticality
 * - Create execution phases
 * - Optimize for parallel execution
 */
export class TestScheduler {
  private readonly defaultPriorities: Record<string, number> = {
    'quantum': 10,      // Highest priority - security critical
    'ai-safety': 10,    // Highest priority - safety critical
    'compliance': 9,    // High priority - certification requirement
    'security': 8,      // High priority - vulnerability detection
    'agentic': 7,       // Medium-high priority
    'stress': 6,        // Medium priority - resource intensive
    'formal': 5,        // Medium priority
    'integration': 4    // Lower priority - depends on others
  };

  /**
   * Schedule tests for execution
   * @param suites Test suites to schedule
   * @returns Execution plan with phases
   */
  schedule(suites: TestSuite[]): ExecutionPlan {
    // Sort suites by priority and dependencies
    const sortedSuites = this.sortByPriorityAndDependencies(suites);
    
    // Create execution phases
    const phases = this.createExecutionPhases(sortedSuites);
    
    // Calculate total tests and duration
    const totalTests = suites.reduce((sum, suite) => sum + suite.tests.length, 0);
    const estimatedDuration = this.estimateDuration(phases);
    
    // Determine parallelism level
    const parallelism = this.calculateParallelism(phases);
    
    return {
      phases,
      totalTests,
      estimatedDuration,
      parallelism
    };
  }

  /**
   * Prioritize tests within a suite
   * @param tests Tests to prioritize
   * @returns Sorted tests by priority
   */
  prioritizeTests(tests: Test[]): Test[] {
    return [...tests].sort((a, b) => {
      // Higher priority first
      const priorityDiff = (b.priority || 5) - (a.priority || 5);
      if (priorityDiff !== 0) return priorityDiff;
      
      // Shorter tests first (for faster feedback)
      const durationDiff = (a.estimatedDuration || 1000) - (b.estimatedDuration || 1000);
      if (durationDiff !== 0) return durationDiff;
      
      // Alphabetical by name
      return a.name.localeCompare(b.name);
    });
  }

  /**
   * Check if tests can run in parallel
   * @param tests Tests to check
   * @returns True if tests can run in parallel
   */
  canRunInParallel(tests: Test[]): boolean {
    // Tests can run in parallel if they don't share tags indicating mutual exclusion
    const exclusiveTags = ['modifies-state', 'requires-exclusive-access', 'stress-test'];
    
    for (const test of tests) {
      if (test.tags?.some(tag => exclusiveTags.includes(tag))) {
        return false;
      }
    }
    
    return true;
  }

  /**
   * Resolve test dependencies
   * @param suites Test suites with dependencies
   * @returns Topologically sorted suites
   */
  private sortByPriorityAndDependencies(suites: TestSuite[]): TestSuite[] {
    // Create dependency graph
    const graph = new Map<string, Set<string>>();
    const suiteMap = new Map<string, TestSuite>();
    
    for (const suite of suites) {
      suiteMap.set(suite.name, suite);
      graph.set(suite.name, new Set(suite.dependencies));
    }
    
    // Topological sort with priority
    const sorted: TestSuite[] = [];
    const visited = new Set<string>();
    const visiting = new Set<string>();
    
    const visit = (name: string) => {
      if (visited.has(name)) return;
      if (visiting.has(name)) {
        throw new Error(`Circular dependency detected: ${name}`);
      }
      
      visiting.add(name);
      const deps = graph.get(name) || new Set();
      
      for (const dep of deps) {
        visit(dep);
      }
      
      visiting.delete(name);
      visited.add(name);
      
      const suite = suiteMap.get(name);
      if (suite) {
        sorted.push(suite);
      }
    };
    
    // Visit suites in priority order
    const prioritySorted = [...suites].sort((a, b) => {
      const priorityDiff = b.priority - a.priority;
      if (priorityDiff !== 0) return priorityDiff;
      return a.name.localeCompare(b.name);
    });
    
    for (const suite of prioritySorted) {
      visit(suite.name);
    }
    
    return sorted;
  }

  /**
   * Create execution phases from sorted suites
   * @param suites Sorted test suites
   * @returns Execution phases
   */
  private createExecutionPhases(suites: TestSuite[]): ExecutionPhase[] {
    const phases: ExecutionPhase[] = [];
    const completed = new Set<string>();
    
    while (completed.size < suites.length) {
      const phase: ExecutionPhase = {
        name: `Phase ${phases.length + 1}`,
        tests: [],
        canRunInParallel: true,
        dependencies: []
      };
      
      // Find suites that can run in this phase
      for (const suite of suites) {
        if (completed.has(suite.name)) continue;
        
        // Check if all dependencies are completed
        const depsCompleted = suite.dependencies.every(dep => completed.has(dep));
        if (!depsCompleted) continue;
        
        // Add tests from this suite
        phase.tests.push(...suite.tests);
        phase.dependencies.push(...suite.dependencies);
        completed.add(suite.name);
        
        // Check if tests can run in parallel
        if (!this.canRunInParallel(suite.tests)) {
          phase.canRunInParallel = false;
        }
      }
      
      if (phase.tests.length === 0) {
        throw new Error('Unable to schedule tests - possible circular dependency');
      }
      
      // Prioritize tests within phase
      phase.tests = this.prioritizeTests(phase.tests);
      
      phases.push(phase);
    }
    
    return phases;
  }

  /**
   * Estimate total execution duration
   * @param phases Execution phases
   * @returns Estimated duration in milliseconds
   */
  private estimateDuration(phases: ExecutionPhase[]): number {
    let totalDuration = 0;
    
    for (const phase of phases) {
      if (phase.canRunInParallel) {
        // Parallel execution - use longest test duration
        const maxDuration = Math.max(
          ...phase.tests.map(t => t.estimatedDuration || 1000)
        );
        totalDuration += maxDuration;
      } else {
        // Sequential execution - sum all test durations
        const sumDuration = phase.tests.reduce(
          (sum, t) => sum + (t.estimatedDuration || 1000),
          0
        );
        totalDuration += sumDuration;
      }
    }
    
    return totalDuration;
  }

  /**
   * Calculate optimal parallelism level
   * @param phases Execution phases
   * @returns Number of parallel workers
   */
  private calculateParallelism(phases: ExecutionPhase[]): number {
    // Find maximum number of tests that can run in parallel
    let maxParallel = 1;
    
    for (const phase of phases) {
      if (phase.canRunInParallel) {
        maxParallel = Math.max(maxParallel, phase.tests.length);
      }
    }
    
    // Limit to reasonable number based on CPU cores
    const cpuCores = typeof navigator !== 'undefined' 
      ? navigator.hardwareConcurrency || 4 
      : 4;
    
    return Math.min(maxParallel, cpuCores * 2);
  }

  /**
   * Get test priority based on category
   * @param category Test category
   * @returns Priority (1-10)
   */
  getPriority(category: string): number {
    return this.defaultPriorities[category] || 5;
  }
}
