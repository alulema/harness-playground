import { Activity } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { StepEvent } from './types';

export default function MetricsChart({ steps }: { steps: StepEvent[] }) {
  const data = steps.filter((step) => step.stage === 'probe').map((step) => ({
    iteration: `Iter ${step.iteration}`,
    score: Math.round(step.probeScore * 100),
  }));
  return (
    <section className="panel rounded-2xl p-5 sm:p-6">
      <div className="flex items-start gap-2">
        <Activity className="accent-text" size={16} />
        <div>
          <h2 className="text-sm font-semibold">Probe performance</h2>
          <p className="muted mt-1 text-xs">Evaluation score by optimization iteration</p>
        </div>
      </div>
      {data.length ? (
        <div className="mt-5 h-[190px] w-full" role="img" aria-label="Probe evaluation score chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="var(--color-border, rgba(255,255,255,0.08))" strokeDasharray="3 5" vertical={false} />
              <XAxis axisLine={false} dataKey="iteration" tick={{ fill: 'var(--color-text-muted, #8b8993)', fontSize: 10 }} tickLine={false} />
              <YAxis axisLine={false} domain={[0, 100]} tick={{ fill: 'var(--color-text-muted, #8b8993)', fontSize: 10 }} tickLine={false} ticks={[0, 25, 50, 75, 100]} />
              <Tooltip contentStyle={{ backgroundColor: 'var(--color-bg-card, #17171e)', border: '1px solid var(--color-border, rgba(255,255,255,0.1))', borderRadius: 10, color: 'var(--color-text, #e4e4e7)', fontSize: 12 }} formatter={(value) => [`${value}%`, 'Score']} />
              <Line activeDot={{ r: 4, strokeWidth: 0 }} dataKey="score" dot={{ r: 3, fill: 'var(--color-accent, #8b70ff)', strokeWidth: 0 }} name="Score" stroke="var(--color-accent, #8b70ff)" strokeWidth={2.5} type="monotone" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="panel-inset muted mt-5 flex h-[190px] items-center justify-center rounded-xl border border-dashed border-[var(--demo-border)] text-xs">
          Probe scores will appear as each iteration is tested.
        </div>
      )}
      <div className="muted mt-3 flex items-center justify-center gap-2 text-[10px]">
        <span className="accent-dot" />Probe score
      </div>
    </section>
  );
}
