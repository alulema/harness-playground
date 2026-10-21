import { Check, Circle, LoaderCircle, Sparkles } from 'lucide-react';
import type { Stage, StepEvent } from './types';

const stages: { id: Stage; description: string }[] = [
  { id: 'propose', description: 'Find a harness improvement' },
  { id: 'probe', description: 'Evaluate task variations' },
  { id: 'compose', description: 'Adopt accepted changes' },
];
const label: Record<StepEvent['component'], string> = {
  system_prompt: 'System prompt',
  memory: 'Memory',
  tool_guidance: 'Tool guidance',
};

export default function LiveExecutionFlow({ stage, steps, isRunning }: { stage: Stage; steps: StepEvent[]; isRunning: boolean }) {
  const index = stages.findIndex((item) => item.id === stage);
  return (
    <section className="panel rounded-2xl p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Optimization loop</h2>
          <p className="muted mt-1 text-xs">Every proposed change is probed before it is composed.</p>
        </div>
        <span className={`status-pill ${isRunning ? 'status-running' : stage === 'completed' ? 'status-done' : ''}`}>
          {isRunning ? <LoaderCircle className="animate-spin" size={12} /> : stage === 'completed' ? <Check size={12} /> : <Circle size={8} />}
          {isRunning ? 'Running' : stage === 'completed' ? 'Complete' : 'Ready'}
        </span>
      </div>
      <div className="relative mt-7 grid grid-cols-3 gap-2">
        <div className="timeline-line" />
        {stages.map((item, i) => {
          const complete = stage === 'completed' || (index > -1 && i < index);
          const active = item.id === stage;
          return (
            <div className="relative flex flex-col items-center text-center" key={item.id}>
              <div className={`timeline-node ${complete ? 'timeline-complete' : active ? 'timeline-active' : ''}`}>
                {complete ? <Check size={14} /> : active && isRunning ? <LoaderCircle className="animate-spin" size={14} /> : <span>{i + 1}</span>}
              </div>
              <p className={`mt-2.5 text-xs font-semibold ${active || complete ? '' : 'muted'}`}>{item.id}</p>
              <p className="muted mt-1 hidden text-[10px] sm:block">{item.description}</p>
            </div>
          );
        })}
      </div>
      <div className="panel-inset mt-6 min-h-[138px] rounded-xl p-3.5">
        <div className="mb-3 flex items-center justify-between">
          <span className="eyebrow">Run activity</span>
          {steps.length > 0 && <span className="muted text-[10px]">{steps.length} events</span>}
        </div>
        {steps.length === 0 ? (
          <div className="muted flex min-h-[82px] items-center justify-center gap-2 text-xs"><Sparkles className="accent-text" size={14} />Your optimization trace will appear here.</div>
        ) : (
          <ol aria-live="polite" className="max-h-[190px] space-y-2 overflow-y-auto pr-1">
            {steps.map((step, i) => (
              <li className="flex items-start gap-2.5 text-xs" key={`${step.iteration}-${step.stage}-${i}`}>
                <span className="activity-dot" />
                <span className="min-w-0 flex-1 leading-relaxed">
                  <b className="capitalize">{step.stage}</b><span className="muted mx-1">·</span>
                  <span className="muted">{label[step.component]}</span><span className="ml-1.5">{step.proposal}</span>
                </span>
                {step.stage === 'probe' && <span className="shrink-0 font-mono text-[10px]">{Math.round(step.probeScore * 100)}%</span>}
                {step.stage === 'compose' && step.accepted && <Check className="positive-text" size={13} />}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
