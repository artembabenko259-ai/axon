const HISTORY_LEN = 24;

export function formatUptime(totalSeconds: number): string {
  const elapsed = Math.max(0, Math.floor(totalSeconds));
  const h = String(Math.floor(elapsed / 3600)).padStart(2, "0");
  const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
  const s = String(elapsed % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

export function sessionElapsedSeconds(sessionStartedAtMs: number | null): number {
  if (!sessionStartedAtMs) return 0;
  return Math.max(0, (Date.now() - sessionStartedAtMs) / 1000);
}

export function pushHistory(series: number[], value: number, max = HISTORY_LEN): number[] {
  const next = [...series, value];
  return next.length > max ? next.slice(-max) : next;
}

/** Ensure sparkline has enough points to render a line. */
export function normalizeSparkline(data: number[]): number[] {
  if (data.length >= 2) return data;
  if (data.length === 1) return [data[0], data[0]];
  return [0, 0];
}

export const METRICS_HISTORY_LEN = HISTORY_LEN;
