import { useCallback, useRef, useState } from 'react';
import { findCachedRun } from './cached';
import type { CachedRun, Domain, ModelOption, RunMetrics, RunResult, Stage, StepEvent } from './types';

interface StreamState {
  stage: Stage;
  steps: StepEvent[];
  result: RunResult | null;
  isRunning: boolean;
  transport: 'live' | 'cached' | null;
  message: string | null;
  error: string | null;
  metrics: RunMetrics;
  modelTokenPreview: string;
  model: string;
}

interface HarnessRequest {
  scenarioId: string;
  domain: Domain;
  prompt: string;
  model: string;
  maxIterations: number;
  tokenBudget: number;
}

interface SseMessage {
  event: string;
  data: Record<string, unknown>;
}

const emptyMetrics: RunMetrics = {
  promptTokens: 0,
  completionTokens: 0,
  totalTokens: 0,
  latencyMs: 0,
  iterations: 0,
};

const initialState: StreamState = {
  stage: 'idle',
  steps: [],
  result: null,
  isRunning: false,
  transport: null,
  message: null,
  error: null,
  metrics: emptyMetrics,
  modelTokenPreview: '',
  model: '',
};

const wait = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function parseBlock(block: string): SseMessage | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue;
    const colon = line.indexOf(':');
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (field === 'event') event = value;
    if (field === 'data') data.push(value);
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join('\n')) as Record<string, unknown> };
  } catch {
    throw new Error('The optimization stream sent invalid JSON.');
  }
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function toStep(event: string, data: Record<string, unknown>): StepEvent | null {
  if (!['baseline', 'propose', 'probe', 'compose'].includes(event)) return null;
  const stage = event as StepEvent['stage'];
  const component = data.component;
  const componentName = component === 'memory' || component === 'tool_guidance' || component === 'system_prompt'
    ? component
    : undefined;
  const instruction = typeof data.instruction === 'string' ? data.instruction : '';
  const rationale = typeof data.rationale === 'string' ? data.rationale : '';
  const status = typeof data.status === 'string' ? data.status : '';

  return {
    iteration: asNumber(data.iteration),
    stage,
    component: componentName,
    proposal: instruction || rationale || status || (stage === 'baseline' ? 'Generating baseline response' : 'Working…'),
    probeScore: asNumber(data.candidateScore),
    baseScore: asNumber(data.baseScore),
    candidateScore: asNumber(data.candidateScore),
    deltaScore: asNumber(data.deltaScore),
    accepted: typeof data.accepted === 'boolean' ? data.accepted : undefined,
    rationale: rationale || undefined,
    status: status || undefined,
  };
}

function cachedResult(cached: CachedRun, steps: StepEvent[], model: string): RunResult {
  return {
    taskId: cached.taskId,
    domain: cached.domain,
    model,
    baseOutput: cached.baseOutput,
    optimizedOutput: cached.optimizedOutput,
    totalImprovement: cached.totalImprovement,
    harness: [],
    acceptedIterations: 0,
    metrics: emptyMetrics,
    evaluation: 'precomputed-demo-trace',
    steps,
  };
}

export function useHarnessStream() {
  const [state, setState] = useState<StreamState>(initialState);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [defaultModel, setDefaultModel] = useState('');
  const controller = useRef<AbortController | null>(null);

  const loadModels = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/models');
      if (!response.ok) throw new Error(`Model service returned HTTP ${response.status}.`);
      const payload = await response.json() as { models: ModelOption[]; defaultModel?: string };
      setModels(payload.models);
      setDefaultModel(payload.defaultModel ?? payload.models[0]?.id ?? '');
      return payload.models;
    } catch {
      setModels([]);
      setDefaultModel('');
      return [];
    }
  }, []);

  const replay = useCallback(async (cached: CachedRun, model: string, message: string, signal?: AbortSignal) => {
    const steps: StepEvent[] = [];
    for (const step of cached.steps) {
      await wait(360);
      if (signal?.aborted) return;
      steps.push(step);
      setState((current) => ({ ...current, stage: step.stage, steps: [...steps], transport: 'cached' }));
    }
    if (signal?.aborted) return;
    setState((current) => ({
      ...current,
      stage: 'completed',
      steps,
      result: cachedResult(cached, steps, model),
      isRunning: false,
      transport: 'cached',
      message,
      error: null,
    }));
  }, []);

  const run = useCallback(async (request: HarnessRequest, mode: 'live' | 'cached') => {
    controller.current?.abort();
    const activeController = new AbortController();
    controller.current = activeController;
    const cached = findCachedRun(request.scenarioId, request.domain);
    setState({
      ...initialState,
      stage: 'baseline',
      isRunning: true,
      transport: mode === 'cached' ? 'cached' : null,
      model: request.model,
      metrics: { ...emptyMetrics },
    });

    if (mode === 'cached') {
      await replay(cached, request.model, 'Replaying a precomputed trace; no model was called.', activeController.signal);
      if (controller.current === activeController) controller.current = null;
      return;
    }

    let receivedEvent = false;
    const steps: StepEvent[] = [];
    let metrics = { ...emptyMetrics };
    const streamUrl = '/api/v1/stream';

    try {
      const response = await fetch(streamUrl, {
        method: 'POST',
        headers: { Accept: 'text/event-stream', 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: request.model,
          domain: request.domain,
          prompt: request.prompt,
          maxIterations: request.maxIterations,
          tokenBudget: request.tokenBudget,
        }),
        signal: activeController.signal,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? `HTTP ${response.status}`);
      }
      if (!response.body) throw new Error('The SSE response has no readable body.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const finalData: { value?: Record<string, unknown> } = {};
      let streamError: string | null = null;
      const consume = (block: string) => {
        const message = parseBlock(block);
        if (!message) return;
        receivedEvent = true;
        const { event, data } = message;

        if (event === 'model_metrics') {
          metrics = {
            promptTokens: metrics.promptTokens + asNumber(data.promptTokens),
            completionTokens: metrics.completionTokens + asNumber(data.completionTokens),
            totalTokens: asNumber(data.totalTokens, metrics.totalTokens + asNumber(data.promptTokens) + asNumber(data.completionTokens)),
            latencyMs: metrics.latencyMs + asNumber(data.latencyMs),
            iterations: metrics.iterations,
          };
          setState((current) => ({ ...current, metrics: { ...metrics } }));
        } else if (event === 'model_token') {
          const token = typeof data.token === 'string' ? data.token : '';
          setState((current) => ({
            ...current,
            modelTokenPreview: `${current.modelTokenPreview}${token}`.slice(-320),
          }));
        } else if (
          (event === 'baseline' && data.status === 'generating') ||
          (event === 'propose' && data.status === 'generating') ||
          (event === 'probe' && (data.status === 'generating' || data.status === 'judging'))
        ) {
          setState((current) => ({ ...current, modelTokenPreview: '' }));
        } else if (event === 'run_started') {
          setState((current) => ({ ...current, model: String(data.model ?? request.model) }));
        } else if (event === 'error') {
          streamError = typeof data.message === 'string' ? data.message : 'Optimization failed.';
        } else if (event === 'completed') {
          finalData.value = data;
        }

        const step = toStep(event, data);
        if (step) {
          steps.push(step);
          if (step.stage === 'probe' && step.status === 'complete') {
            metrics.iterations = Math.max(metrics.iterations, step.iteration);
          }
          setState((current) => ({
            ...current,
            stage: step.stage,
            steps: [...steps],
            metrics: { ...metrics },
          }));
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() ?? '';
        blocks.forEach(consume);
        if (done) break;
      }
      if (buffer.trim()) consume(buffer);

      if (streamError) throw new Error(streamError);
      const completion = finalData.value;
      if (!completion) throw new Error('The optimization stream ended before completion.');
      const finalMetrics = (completion.metrics ?? metrics) as RunMetrics;
      const result: RunResult = {
        taskId: `live-${Date.now()}`,
        domain: request.domain,
        model: String(completion.model ?? request.model),
        baseOutput: String(completion.baseOutput ?? ''),
        optimizedOutput: String(completion.optimizedOutput ?? ''),
        totalImprovement: asNumber(completion.totalImprovement),
        harness: Array.isArray(completion.harness) ? completion.harness.filter((item): item is string => typeof item === 'string') : [],
        acceptedIterations: asNumber(completion.acceptedIterations),
        metrics: finalMetrics,
        evaluation: String(completion.evaluation ?? 'same-model-judge'),
        steps,
      };
      setState((current) => ({
        ...current,
        stage: 'completed',
        steps,
        result,
        isRunning: false,
        transport: 'live',
        message: `Evaluated live with ${result.model}; judge scores are model estimates, not objective benchmarks.`,
        metrics: finalMetrics,
      }));
    } catch (error) {
      if (activeController.signal.aborted) return;
      if (!receivedEvent && error instanceof Error && !activeController.signal.aborted) {
        await replay(
          cached,
          request.model,
          `Live model service unavailable (${error.message}); replayed the cached example. Choose a cached replay for examples.`,
        );
      } else {
        const message = error instanceof Error ? error.message : 'Optimization failed.';
        setState((current) => ({
          ...current,
          stage: 'error',
          isRunning: false,
          error: message,
          metrics,
        }));
      }
    } finally {
      if (controller.current === activeController) controller.current = null;
    }
  }, [replay]);

  const reset = useCallback(() => {
    controller.current?.abort();
    controller.current = null;
    setState(initialState);
  }, []);

  return { ...state, models, defaultModel, loadModels, run, reset };
}
