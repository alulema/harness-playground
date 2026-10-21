import { useMemo, useState } from 'react';
import { ArrowUpRight, Bolt, Code2, RotateCcw, Sparkles } from 'lucide-react';
import { cachedRuns } from './cached';
import { useHarnessStream } from './useHarnessStream';
import DiffViewer from './DiffViewer';
import LiveExecutionFlow from './LiveExecutionFlow';
import MetricsChart from './MetricsChart';
import TaskSelector from './TaskSelector';
import type { Domain, Mode } from './types';

const firstRun = cachedRuns[0];

export default function Playground() {
  const [domain, setDomain] = useState<Domain>(firstRun.domain);
  const [scenarioId, setScenarioId] = useState(firstRun.id);
  const [prompt, setPrompt] = useState(firstRun.prompt);
  const [mode, setMode] = useState<Mode>('live');
  const runState = useHarnessStream();
  const selectedRun = useMemo(
    () => cachedRuns.find((run) => run.id === scenarioId) ?? cachedRuns.find((run) => run.domain === domain)!,
    [domain, scenarioId],
  );

  async function startRun() {
    if (!prompt.trim()) return;
    await runState.run({ scenarioId, domain, prompt: prompt.trim() }, domain, mode);
  }

  return (
    <main className="mx-auto min-h-screen max-w-[1280px] px-4 pb-14 pt-6 sm:px-7 sm:pt-10 lg:px-10">
      <header className="mb-9 flex flex-wrap items-center justify-between gap-4 border-b border-[var(--demo-border)] pb-5">
        <a className="flex items-center gap-3 text-[var(--color-text,#f4f3f7)] no-underline" href="/">
          <div className="brand-mark">H²</div>
          <div><span className="block text-sm font-semibold">Harness²</span><span className="muted block text-[10px] tracking-wide">AGENT OPTIMIZATION LAB</span></div>
        </a>
        <span className="status-pill"><span className="live-dot" />Interactive demo</span>
      </header>

      <section className="mx-auto mb-9 max-w-3xl text-center">
        <div className="badge mb-4"><Sparkles size={12} />Recursive agent improvement</div>
        <h1 className="text-balance text-3xl font-semibold tracking-[-0.04em] sm:text-5xl">
          Better agents, <span className="accent-gradient">one loop at a time.</span>
        </h1>
        <p className="muted mx-auto mt-4 max-w-2xl text-sm leading-6 sm:text-base sm:leading-7">
          Watch Harness² refine prompts, memory, and tool guidance through a measurable cycle of <span className="text-[var(--color-text,#f4f3f7)]">Propose → Probe → Compose</span>.
        </p>
      </section>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="muted flex items-center gap-2 text-xs"><span className="eyebrow">01</span>Configure an optimization run</div>
        <div className="mode-switch" aria-label="Execution mode">
          {(['live', 'cached'] as Mode[]).map((item) => (
            <button aria-pressed={mode === item} className={`mode-button ${mode === item ? 'mode-selected' : ''}`} disabled={runState.isRunning} key={item} onClick={() => setMode(item)} type="button">
              {item === 'live' ? <Bolt size={12} /> : <RotateCcw size={12} />}{item === 'live' ? 'Live stream' : 'Cached replay'}
            </button>
          ))}
        </div>
      </div>
      <TaskSelector
        domain={domain}
        scenarioId={scenarioId}
        prompt={prompt}
        disabled={runState.isRunning}
        onDomain={setDomain}
        onScenario={setScenarioId}
        onPrompt={setPrompt}
      />
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="muted min-h-5 text-xs">
          {runState.message ?? (mode === 'live'
            ? 'Live mode streams a demonstration trace; no external model is called.'
            : 'Cached mode replays a precomputed evaluation trace.')}
        </p>
        <button className="button-primary" disabled={runState.isRunning || !prompt.trim()} onClick={startRun} type="button">
          {runState.isRunning ? <span className="spinner" /> : <Sparkles size={15} />}
          {runState.isRunning ? 'Optimizing…' : 'Run Harness² optimization'}
          {!runState.isRunning && <ArrowUpRight size={14} />}
        </button>
      </div>

      <div className="muted mb-4 mt-9 flex items-center gap-2 text-xs">
        <span className="eyebrow">02</span>Observe the optimization
        {runState.result && <button className="ml-auto text-[11px] transition hover:text-[var(--color-text,#fff)]" onClick={runState.reset} type="button">Clear run</button>}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <LiveExecutionFlow stage={runState.stage} steps={runState.steps} isRunning={runState.isRunning} />
        <MetricsChart steps={runState.steps} />
      </div>

      <div className="muted mb-4 mt-9 flex items-center gap-2 text-xs">
        <span className="eyebrow">03</span>Compare the outcome
        {runState.result && <span className="muted ml-auto hidden font-mono text-[10px] sm:inline">{runState.result.taskId}</span>}
      </div>
      <DiffViewer result={runState.result} />

      <footer className="muted mt-8 flex flex-col items-center justify-between gap-3 border-t border-[var(--demo-border)] pt-5 text-[11px] sm:flex-row">
        <p>{selectedRun.title} · example trace</p>
        <a className="inline-flex items-center gap-1.5 transition hover:text-[var(--color-text,#fff)]" href="https://github.com/alulema/harness-playground" rel="noreferrer" target="_blank">
          <Code2 size={13} />Source <ArrowUpRight size={11} />
        </a>
      </footer>
    </main>
  );
}
