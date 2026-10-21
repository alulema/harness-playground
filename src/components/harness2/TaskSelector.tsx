import { FlaskConical } from 'lucide-react';
import { cachedRuns } from './cached';
import type { Domain } from './types';

interface Props {
  domain: Domain;
  scenarioId: string;
  prompt: string;
  disabled: boolean;
  onDomain: (value: Domain) => void;
  onScenario: (value: string) => void;
  onPrompt: (value: string) => void;
}

const domains: Domain[] = ['Legal LAB', 'JobBench', 'WorkBuddy'];

export default function TaskSelector({ domain, scenarioId, prompt, disabled, onDomain, onScenario, onPrompt }: Props) {
  const options = cachedRuns.filter((run) => run.domain === domain);

  function changeDomain(value: Domain) {
    onDomain(value);
    if (scenarioId !== 'custom') {
      const first = cachedRuns.find((run) => run.domain === value)!;
      onScenario(first.id);
      onPrompt(first.prompt);
    }
  }

  function changeScenario(value: string) {
    onScenario(value);
    onPrompt(value === 'custom' ? '' : cachedRuns.find((run) => run.id === value)?.prompt ?? '');
  }

  return (
    <section className="panel rounded-2xl p-5 sm:p-6">
      <div className="mb-5 flex items-start gap-3">
        <div className="icon-chip"><FlaskConical size={18} /></div>
        <div>
          <h2 className="text-sm font-semibold">Choose an optimization task</h2>
          <p className="muted mt-1 text-xs">Select a domain and explore how an agent can improve.</p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">
          Domain
          <select className="field-control" disabled={disabled} value={domain} onChange={(event) => changeDomain(event.target.value as Domain)}>
            {domains.map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
        <label className="field-label">
          Scenario
          <select className="field-control" disabled={disabled} value={scenarioId} onChange={(event) => changeScenario(event.target.value)}>
            {options.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
            <option value="custom">Custom prompt</option>
          </select>
        </label>
      </div>
      <label className="field-label mt-4">
        Task prompt
        <textarea
          aria-label="Task prompt"
          className="field-control min-h-24 resize-y py-3 leading-relaxed"
          disabled={disabled}
          maxLength={1200}
          placeholder="Describe a task for the agent to optimize..."
          value={prompt}
          onChange={(event) => onPrompt(event.target.value)}
        />
      </label>
      <div className="muted mt-2 flex justify-between text-[11px]">
        <span>{scenarioId === 'custom' ? 'Custom prompts replay the selected domain trace in this demo.' : 'The task prompt is editable.'}</span>
        <span>{prompt.length}/1200</span>
      </div>
    </section>
  );
}
