import { useEffect, useState } from 'react';
import { Check, Circle, LoaderCircle, Sparkles } from 'lucide-react';
import type { Stage, StepEvent } from './types';

const stages: { id: Stage; description: string }[] = [
  { id: 'propose', description: 'Find a harness improvement' },
  { id: 'probe', description: 'Evaluate task variations' },
  { id: 'compose', description: 'Adopt accepted changes' },
];
const label: Record<NonNullable<StepEvent['component']>, string> = {
  system_prompt: 'System prompt',
  memory: 'Memory',
  tool_guidance: 'Tool guidance',
};

export default function LiveExecutionFlow({
  stage,
  steps,
  isRunning,
  modelTokenPreview,
}: {
  stage: Stage;
  steps: StepEvent[];
  isRunning: boolean;
  modelTokenPreview: string;
}) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!isRunning) return;
    const started = Date.now();
    setElapsed(0);
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [isRunning]);
  const last = steps[steps.length - 1];
  const phase = last ? (last.status === 'generating' || last.status === 'judging' ? last.status : 'working') : 'starting';
  const index = stages.findIndex((item) => item.id === stage);
  return (
    <section className="panel rounded-2xl p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Optimization loop</h2>
          <p className="muted mt-1 text-xs">Every proposed change is probed before it is composed.</p>
        </div>
        <span className={`status-pill ${isRunning ? 'status-running' : stage === 'completed' ? 'status-done' : stage === 'error' ? 'status-error' : ''}`}>
          {isRunning ? <LoaderCircle className="animate-spin" size={12} /> : stage === 'completed' ? <Check size={12} /> : stage === 'error' ? <Circle size={8} /> : <Circle size={8} />}
          {isRunning ? 'Running' : stage === 'completed' ? 'Complete' : stage === 'error' ? 'Stopped' : 'Ready'}
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
          {isRunning ? (
            <span className="muted text-[10px]">{phase} · {elapsed}s · small CPU model, ~1–2 min per iteration</span>
          ) : (
            steps.length > 0 && <span className="muted text-[10px]">{steps.length} events</span>
          )}
        </div>
        {steps.length === 0 ? (
          <div className="muted flex min-h-[82px] items-center justify-center gap-2 text-xs"><Sparkles className="accent-text" size={14} />Your optimization trace will appear here.</div>
        ) : (
          <ol aria-live="polite" className="max-h-[190px] space-y-2 overflow-y-auto pr-1">
            {steps.map((step, i) => (
              <li className="flex items-start gap-2.5 text-xs" key={`${step.iteration}-${step.stage}-${i}`}>
                <span className="activity-dot" />
                <span className="min-w-0 flex-1 leading-relaxed">
                  {step.iteration > 0 && <span className="muted mr-1">#{step.iteration}</span>}
                  <b className="capitalize">{step.stage}</b>
                  {step.component && <><span className="muted mx-1">·</span><span className="muted">{label[step.component]}</span></>}
                  {step.proposal && <span className="ml-1.5">{step.proposal}</span>}
                  {step.stage === 'probe' && step.status === 'complete' && (
                    <span className={`ml-1.5 ${step.accepted ? 'positive-text' : 'muted'}`}>
                      {step.accepted ? 'adopted' : 'not adopted'} · {Math.round(step.baseScore ?? 0)} → {Math.round(step.candidateScore ?? 0)}
                    </span>
                  )}
                </span>
                {step.stage === 'compose' && step.accepted === true && <Check className="positive-text" size={13} />}
                {step.stage === 'compose' && step.accepted === false && <span className="muted text-[10px]">kept previous</span>}
              </li>
            ))}
          </ol>
        )}
        {isRunning && modelTokenPreview && (
          <div className="mt-3 border-t border-[var(--demo-border)] pt-3">
            <span className="eyebrow">Model output · streaming</span>
            <pre aria-live="polite" className="muted mt-2 max-h-16 overflow-hidden whitespace-pre-wrap break-words text-[11px] leading-relaxed">
              {modelTokenPreview}
            </pre>
          </div>
        )}
      </div>
    </section>
  );
}
