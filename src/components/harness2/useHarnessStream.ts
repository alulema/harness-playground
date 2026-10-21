import { useCallback, useRef, useState } from 'react';
import { findCachedRun } from './cached';
import type { CachedRun, Domain, Mode, RunResult, Stage, StepEvent } from './types';

interface StreamState {
  stage: Stage;
  steps: StepEvent[];
  result: RunResult | null;
  isRunning: boolean;
  transport: 'live' | 'cached' | null;
  message: string | null;
}

interface StreamPayload extends Partial<StepEvent>, Partial<RunResult> {
  result?: Partial<RunResult>;
}

interface HarnessRequest {
  scenarioId: string;
  domain: Domain;
  prompt: string;
}

const initialState: StreamState = {
  stage: 'idle',
  steps: [],
  result: null,
  isRunning: false,
  transport: null,
  message: null,
};

const wait = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function isStage(value: unknown): value is StepEvent['stage'] {
  return value === 'propose' || value === 'probe' || value === 'compose';
}

function parseBlock(block: string): { event: string; data: string } | null {
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
  return data.length ? { event, data: data.join('\n') } : null;
}

function toStep(event: string, payload: StreamPayload): StepEvent | null {
  const stage = isStage(payload.stage) ? payload.stage : isStage(event) ? event : null;
  if (!stage) return null;
  const component = payload.component;
  return {
    iteration: Number.isFinite(payload.iteration) ? Number(payload.iteration) : 1,
    stage,
    component: component === 'memory' || component === 'tool_guidance' ? component : 'system_prompt',
    proposal: typeof payload.proposal === 'string' ? payload.proposal : 'Harness update received.',
    probeScore: Number.isFinite(payload.probeScore) ? Number(payload.probeScore) : 0,
    accepted: typeof payload.accepted === 'boolean' ? payload.accepted : false,
    deltaScore: Number.isFinite(payload.deltaScore) ? Number(payload.deltaScore) : 0,
  };
}

function normalizeResult(
  payload: Partial<RunResult>,
  request: HarnessRequest,
  steps: StepEvent[],
  fallback: CachedRun,
): RunResult {
  return {
    taskId: payload.taskId ?? fallback.taskId,
    domain: payload.domain ?? request.domain,
    baseOutput: payload.baseOutput ?? fallback.baseOutput,
    optimizedOutput: payload.optimizedOutput ?? fallback.optimizedOutput,
    totalImprovement: Number.isFinite(payload.totalImprovement)
      ? Number(payload.totalImprovement)
      : fallback.totalImprovement,
    steps,
  };
}

export function useHarnessStream() {
  const [state, setState] = useState<StreamState>(initialState);
  const controller = useRef<AbortController | null>(null);

  const replay = useCallback(async (request: HarnessRequest, cached: CachedRun, message: string | null) => {
    const steps: StepEvent[] = [];
    for (const step of cached.steps) {
      await wait(360);
      steps.push(step);
      setState((current) => ({ ...current, stage: step.stage, steps: [...steps], transport: 'cached' }));
    }
    setState((current) => ({
      ...current,
      stage: 'completed',
      steps,
      result: normalizeResult(cached, request, steps, cached),
      isRunning: false,
      transport: 'cached',
      message,
    }));
  }, []);

  const run = useCallback(async (request: HarnessRequest, domain: Domain, mode: Mode) => {
    controller.current?.abort();
    const cached = findCachedRun(request.scenarioId, domain);
    setState({ ...initialState, isRunning: true, transport: mode === 'cached' ? 'cached' : null });

    if (mode === 'cached') {
      await replay(request, cached, null);
      return;
    }

    const activeController = new AbortController();
    controller.current = activeController;
    let timer: number | undefined;
    const steps: StepEvent[] = [];
    let finalResult: Partial<RunResult> | null = null;
    let sawDone = false;
    try {
      const endpoint = import.meta.env.PUBLIC_HARNESS_STREAM_URL || '/api/harness/stream';
      timer = window.setTimeout(() => activeController.abort(), 5_000);
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { Accept: 'text/event-stream', 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...request, mode }),
        signal: activeController.signal,
      });
      if (timer !== undefined) window.clearTimeout(timer);
      timer = undefined;
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error('SSE response has no readable body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const consume = (block: string) => {
        const message = parseBlock(block);
        if (!message) return;
        let payload: StreamPayload;
        try {
          payload = JSON.parse(message.data) as StreamPayload;
        } catch {
          throw new Error('SSE event contains invalid JSON');
        }
        const step = toStep(message.event, payload);
        if (step) {
          steps.push(step);
          setState((current) => ({
            ...current,
            stage: step.stage,
            steps: [...steps],
            transport: 'live',
          }));
        }
        if (message.event === 'output') {
          finalResult = payload.result ?? payload;
        }
        if (message.event === 'completed') {
          finalResult = payload.result ?? payload;
          sawDone = true;
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
      if (!sawDone) throw new Error('SSE stream closed before the completed event');

      setState((current) => ({
        ...current,
        stage: 'completed',
        steps,
        result: normalizeResult(finalResult ?? {}, request, steps, cached),
        isRunning: false,
        transport: 'live',
        message: null,
      }));
    } catch (error) {
      if (activeController.signal.aborted && !steps.length) {
        await replay(request, cached, 'Live stream unavailable; replaying the cached evaluation trace.');
      } else {
        await replay(
          request,
          cached,
          `Live stream interrupted${error instanceof Error ? ` (${error.message})` : ''}; replayed the cached trace.`,
        );
      }
    } finally {
      if (timer !== undefined) window.clearTimeout(timer);
      if (controller.current === activeController) controller.current = null;
    }
  }, [replay]);

  const reset = useCallback(() => {
    controller.current?.abort();
    controller.current = null;
    setState(initialState);
  }, []);

  return { ...state, run, reset };
}
