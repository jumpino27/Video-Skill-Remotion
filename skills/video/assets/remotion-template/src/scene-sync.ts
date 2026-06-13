import { useVideoConfig } from "remotion";
import type { Caption } from "@remotion/captions";

/**
 * Compute per-scene frame ranges that are SYNCED to the narration: scene changes
 * land on the biggest pauses in the voice (i.e. sentence boundaries), instead of
 * fixed proportional weights. Falls back to equal slices if the audio doesn't have
 * enough clear pauses.
 */
export function useSceneCuts(
  captions: Caption[] | undefined,
  count: number,
  cutMs?: number[]
): { from: number; len: number }[] {
  const { durationInFrames, fps } = useVideoConfig();
  // Explicit cut times (ms) win: use when the narration's biggest pauses are NOT
  // the beat boundaries (e.g. ellipsis pauses inside a sentence). Pass the start
  // times of each beat's first word, read from captions.json.
  const explicit =
    cutMs && cutMs.length === count - 1
      ? [0, ...cutMs.map((m) => Math.min(durationInFrames - 1, Math.round((m / 1000) * fps))), durationInFrames]
      : null;
  const bounds =
    explicit ??
    captionCuts(captions, count, fps, durationInFrames) ??
    equalBounds(count, durationInFrames);
  const out: { from: number; len: number }[] = [];
  for (let i = 0; i < count; i++) out.push({ from: bounds[i], len: bounds[i + 1] - bounds[i] });
  return out;
}

function equalBounds(count: number, dur: number): number[] {
  const b: number[] = [];
  for (let i = 0; i <= count; i++) b.push(Math.round((dur * i) / count));
  return b;
}

function captionCuts(
  captions: Caption[] | undefined,
  count: number,
  fps: number,
  dur: number
): number[] | null {
  if (!captions || captions.length < count + 1) return null;
  const totalMs = captions[captions.length - 1].endMs;
  const minMs = 1100; // keep cuts away from each other and the ends
  const gaps: { mid: number; gap: number }[] = [];
  for (let i = 1; i < captions.length; i++) {
    gaps.push({ mid: (captions[i].startMs + captions[i - 1].endMs) / 2, gap: captions[i].startMs - captions[i - 1].endMs });
  }
  const sorted = [...gaps].sort((a, b) => b.gap - a.gap);
  const chosen: number[] = [];
  for (const g of sorted) {
    if (chosen.length >= count - 1) break;
    if (g.mid < minMs || totalMs - g.mid < minMs) continue;
    if (chosen.every((c) => Math.abs(c - g.mid) > minMs)) chosen.push(g.mid);
  }
  if (chosen.length < count - 1) return null; // not enough clear pauses → fall back
  chosen.sort((a, b) => a - b);
  return [0, ...chosen.map((m) => Math.round((m / 1000) * fps)), dur];
}
