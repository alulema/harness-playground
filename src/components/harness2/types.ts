export type Stage = 'idle' | 'baseline' | 'propose' | 'probe' | 'compose' | 'completed' | 'error';
export type ComponentName = 'system_prompt' | 'memory' | 'tool_guidance';
export type Domain = 'Legal LAB' | 'JobBench' | 'WorkBuddy';
export type Mode = 'live' | 'cached';

export interface StepEvent {
  iteration: number;
  stage: 'baseline' | 'propose' | 'probe' | 'compose';
  component?: ComponentName;
  proposal: string;
  probeScore?: number;
  accepted?: boolean;
  deltaScore?: number;
  baseScore?: number;
  candidateScore?: number;
  rationale?: string;
  status?: string;
}

export interface ModelOption {
  id: string;
  name: string;
  size?: number;
  family?: string;
  parameterSize?: string;
  bundled?: boolean;
}

export interface RunMetrics {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  latencyMs: number;
  iterations: number;
}

export interface CachedRun {
  id: string;
  title: string;
  description: string;
  prompt: string;
  taskId: string;
  domain: Domain;
  baseOutput: string;
  optimizedOutput: string;
  totalImprovement: number;
  steps: StepEvent[];
}

export interface RunResult {
  taskId: string;
  domain: Domain;
  model: string;
  baseOutput: string;
  optimizedOutput: string;
  totalImprovement: number;
  harness: string[];
  acceptedIterations: number;
  metrics: RunMetrics;
  evaluation: string;
  steps: StepEvent[];
}
