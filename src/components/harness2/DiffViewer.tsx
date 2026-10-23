import { ArrowRight, GitCompareArrows } from 'lucide-react';
import type { RunResult } from './types';

function OutputCard({ label, value, optimized }: { label: string; value: string; optimized?: boolean }) {
  return (
    <article className={`min-w-0 rounded-xl border p-4 ${optimized ? 'border-emerald-400/20 bg-emerald-400/[0.035]' : 'border-[var(--demo-border)] bg-[var(--demo-bg)]'}`}>
      <h3 className={`mb-3 text-[11px] font-semibold uppercase tracking-[0.13em] ${optimized ? 'positive-text' : 'muted'}`}>{label}</h3>
      <p className="whitespace-pre-wrap text-sm leading-6">{value}</p>
    </article>
  );
}

export default function DiffViewer({ result }: { result: RunResult | null }) {
  return (
    <section className="panel rounded-2xl p-5 sm:p-6">
      <div className="mb-5 flex items-center gap-2.5">
        <GitCompareArrows className="accent-text" size={17} />
        <div>
          <h2 className="text-sm font-semibold">Agent output comparison</h2>
          <p className="muted mt-1 text-xs">Base response versus Harness² optimized response</p>
        </div>
      </div>
      {result ? (
        <>
          <div className="mb-3 grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
            <OutputCard label="Base agent" value={result.baseOutput} />
            <div className="muted flex items-center justify-center py-1"><ArrowRight className="hidden md:block" size={16} /><span className="text-[10px] uppercase tracking-widest md:hidden">Optimized</span></div>
            <OutputCard label={`Optimized · ${result.model}`} value={result.optimizedOutput} optimized />
          </div>
          <div className="panel-inset rounded-xl p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="eyebrow">Composed system prompt</h3>
              <span className="muted text-[10px]">{result.harness.length} adopted rules</span>
            </div>
            {result.harness.length ? (
              <ol className="space-y-2">
                {result.harness.map((rule, index) => (
                  <li className="flex items-start gap-2 text-xs leading-relaxed" key={`${index}-${rule}`}>
                    <span className="positive-text mt-0.5">+ </span><span>{rule}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted text-xs">
                {result.evaluation === 'precomputed-demo-trace'
                  ? 'This example trace does not include the composed harness instructions.'
                  : 'No proposed rule improved the model-judge score, so the original harness was kept.'}
              </p>
            )}
          </div>
          <p className="muted mt-3 text-[10px]">
            {result.evaluation === 'precomputed-demo-trace'
              ? 'Precomputed illustrative score'
              : 'Same-model LLM judge · comparative estimate'}
            {' · '}final score {Math.round(result.totalImprovement)}/100 · not an objective benchmark.
          </p>
        </>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {['Base agent', 'Harness² optimized'].map((item) => (
            <div className="panel-inset min-h-[150px] rounded-xl border border-dashed border-[var(--demo-border)] p-4" key={item}>
              <p className="eyebrow">{item}</p>
              <div className="mt-5 space-y-2">
                <div className="skeleton w-full" /><div className="skeleton w-11/12" /><div className="skeleton w-3/4" />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
