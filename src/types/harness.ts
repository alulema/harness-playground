export type HarnessStage = 'idle' | 'propose' | 'probe' | 'compose' | 'completed';
export type HarnessComponent = 'system_prompt' | 'memory' | 'tool_guidance';
export type HarnessDomain = 'Legal LAB' | 'JobBench' | 'WorkBuddy';
export type ExecutionMode = 'live' | 'cached';

export interface HarnessStepEvent {
  iteration: number;
  stage: Exclude<HarnessStage, 'idle' | 'completed'>;
  component: HarnessComponent;
  proposal: string;
  probeScore: number;
  accepted: boolean;
  deltaScore: number;
}

export interface HarnessRunResult {
  taskId: string;
  domain: HarnessDomain;
  baseOutput: string;
  optimizedOutput: string;
  totalImprovement: number;
  steps: HarnessStepEvent[];
}

export interface CachedHarnessRun extends HarnessRunResult {
  id: string;
  title: string;
  description: string;
  prompt: string;
}

export interface HarnessRequest {
  scenarioId: string;
  domain: HarnessDomain;
  prompt: string;
  mode: ExecutionMode;
}
