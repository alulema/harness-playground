import { Cpu, FlaskConical } from 'lucide-react';
import { cachedRuns } from './cached';
import type { Domain, ModelOption } from './types';

interface Props {
  domain: Domain;
  scenarioId: string;
  prompt: string;
  model: string;
  models: ModelOption[];
  maxIterations: number;
  tokenBudget: number;
  disabled: boolean;
  onDomain: (value: Domain) => void;
  onScenario: (value: string) => void;
  onPrompt: (value: string) => void;
  onModel: (value: string) => void;
  onIterations: (value: number) => void;
  onTokenBudget: (value: number) => void;
}

const domains: Domain[] = ['Legal LAB', 'JobBench', 'WorkBuddy'];

export default function ModelAndDomainSelector({
  domain,
  scenarioId,
  prompt,
  model,
  models,
  maxIterations,
  tokenBudget,
  disabled,
  onDomain,
  onScenario,
  onPrompt,
  onModel,
  onIterations,
  onTokenBudget,
}: Props) {
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
          <h2 className="text-sm font-semibold">Configure a live optimization</h2>
          <p className="muted mt-1 text-xs">Choose a local model, domain, and bounded evaluation budget.</p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">
          Local model
          <select className="field-control" disabled={disabled || models.length === 0} value={model} onChange={(event) => onModel(event.target.value)}>
            {models.length === 0 && <option value="">No local Ollama models detected</option>}
            {models.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}{item.parameterSize ? ` · ${item.parameterSize}` : ''}{item.bundled ? ' · bundled' : ''}
              </option>
            ))}
          </select>
        </label>
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
        <label className="field-label">
          Iterations
          <select className="field-control" disabled={disabled} value={maxIterations} onChange={(event) => onIterations(Number(event.target.value))}>
            <option value={1}>1 iteration · recommended, faster</option>
            <option value={2}>2 iterations · deeper, slower</option>
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
      <div className="muted mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px]">
        <span>{scenarioId === 'custom' ? 'Custom tasks are evaluated live by the selected local model.' : 'The selected prompt is sent to your local model.'}</span>
        <span>{prompt.length}/1200</span>
      </div>
      <div className="panel-inset muted mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-[11px]">
        <span className="flex items-center gap-2"><Cpu className="accent-text" size={14} />Maximum token budget</span>
        <select
          aria-label="Maximum token budget"
          className="field-control !min-h-8 !w-auto !py-1 text-xs"
          disabled={disabled}
          value={tokenBudget}
          onChange={(event) => onTokenBudget(Number(event.target.value))}
        >
          <option value={2048}>2,048 tokens</option>
          <option value={4096}>4,096 tokens</option>
          <option value={8192}>8,192 tokens</option>
        </select>
      </div>
    </section>
  );
}
