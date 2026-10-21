export type Stage = 'idle' | 'propose' | 'probe' | 'compose' | 'completed';
export type ComponentName = 'system_prompt' | 'memory' | 'tool_guidance';
export type Domain = 'Legal LAB' | 'JobBench' | 'WorkBuddy';
export type Mode = 'live' | 'cached';

export interface StepEvent {
  iteration: number;
  stage: Exclude<Stage, 'idle' | 'completed'>;
  component: ComponentName;
  proposal: string;
  probeScore: number;
  accepted: boolean;
  deltaScore: number;
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
  baseOutput: string;
  optimizedOutput: string;
  totalImprovement: number;
  steps: StepEvent[];
}
