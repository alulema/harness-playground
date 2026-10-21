import runs from '../../data/harness2-cached-runs.json';
import type { CachedRun, Domain } from './types';

export const cachedRuns = runs as CachedRun[];

export function findCachedRun(id: string, domain: Domain): CachedRun {
  return cachedRuns.find((run) => run.id === id && run.domain === domain)
    ?? cachedRuns.find((run) => run.domain === domain)
    ?? cachedRuns[0];
}
