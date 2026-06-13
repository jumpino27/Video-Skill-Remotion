#!/usr/bin/env node
// Generate narration audio with ElevenLabs **Eleven v3** (the house TTS for /video + /luma).
//
// Usage:
//   node generate-voice-elevenlabs.mjs --script-file script.txt --out public/voice.mp3 \
//        [--voice-id eXO2dNYP4zo4oPWzuLta] [--model-id eleven_v3] \
//        [--stability natural|creative|robust|<0..1>] [--similarity 0.75] \
//        [--speed 1.0] [--language en] [--seed 1234] [--format mp3_44100_128] [--text "..."]
//
// Eleven v3 (`eleven_v3`) is the most expressive model: it understands inline AUDIO TAGS
// written in square brackets directly in the text — e.g. [excited], [whispers], [sighs],
// [laughs], [sarcastic], [pause], [strong French accent] — plus punctuation cues
// (ellipses … = pause/weight, CAPITALS = emphasis). No SSML: v3 does NOT support
// <break> tags; control pacing with tags + punctuation.
//
// Stability for v3 is DISCRETE — only three values are accepted:
//   creative = 0.0  (most emotional/expressive, best audio-tag response, can hallucinate)
//   natural  = 0.5  (balanced, closest to the original voice)  ← default
//   robust   = 1.0  (very stable, but weak response to audio tags)
// Numeric values are snapped to the nearest of {0, 0.5, 1} when model is eleven_v3.
//
// Voice: defaults to the house voice "Ivy" eXO2dNYP4zo4oPWzuLta — energetic young British
// female (designed with eleven_ttv_v3 for social media; fluent multilingual incl. de/it/ro).
// Keep each request under ~3000 chars (chunk longer scripts and concat with ffmpeg).
// Output formats: mp3_44100_128 (default), mp3_44100_192, wav_44100, pcm_44100, opus_48000_128, …
import fs from "node:fs";
import path from "node:path";
import { getElevenLabsKey, loadPersona, parseArgs, die } from "./_shared.mjs";

const args = parseArgs(process.argv.slice(2));
let text = args.text;
if (args["script-file"]) text = fs.readFileSync(args["script-file"], "utf8");
if (!text || !text.trim()) die("Provide --text or --script-file");
text = text.trim();

// Voice resolves: --voice-id flag > VIDEO_VOICE_ID env > persona config > a public default.
const persona = loadPersona();
const voiceId =
  args["voice-id"] ||
  process.env.VIDEO_VOICE_ID ||
  persona?.voice?.id ||
  "eXO2dNYP4zo4oPWzuLta"; // fallback: ElevenLabs "Ivy" (energetic British, social-media)
const modelId =
  args["model-id"] || process.env.VIDEO_MODEL_ID || persona?.voice?.model || "eleven_v3";
const format = args.format || "mp3_44100_128";
const out = args.out || "voice.mp3";

if (text.length > 3000)
  console.error(
    `WARN: script is ${text.length} chars (> ~3000). v3 may truncate/destabilize — ` +
      `consider chunking into multiple calls and concatenating with ffmpeg.`
  );

// --- stability: accept presets or a number; v3 only allows 0 / 0.5 / 1 ---
const PRESETS = { creative: 0.0, natural: 0.5, robust: 1.0 };
let stability = 0.5;
if (args.stability != null) {
  const s = String(args.stability).toLowerCase();
  if (s in PRESETS) stability = PRESETS[s];
  else if (!Number.isNaN(Number(s))) stability = Math.min(1, Math.max(0, Number(s)));
  else die(`--stability must be creative|natural|robust or a number 0..1 (got "${args.stability}")`);
}
if (modelId === "eleven_v3") {
  // snap to the nearest discrete v3 value
  stability = [0, 0.5, 1].reduce((a, b) => (Math.abs(b - stability) < Math.abs(a - stability) ? b : a));
}

const voice_settings = {
  stability,
  similarity_boost: args.similarity != null ? Number(args.similarity) : 0.75,
  use_speaker_boost: true,
};
// speed lives in voice_settings (0.7–1.2; 1.0 = unchanged)
if (args.speed != null) voice_settings.speed = Math.min(1.2, Math.max(0.7, Number(args.speed)));

const body = { text, model_id: modelId, voice_settings };
if (args.language) body.language_code = args.language; // ISO 639-1, e.g. en, ro, de
if (args.seed != null) body.seed = Number(args.seed); // best-effort reproducibility

const url = `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}?output_format=${encodeURIComponent(format)}`;
const res = await fetch(url, {
  method: "POST",
  headers: { "xi-api-key": getElevenLabsKey(), "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
if (!res.ok) die(`ElevenLabs TTS failed (${res.status}): ${await res.text()}`);

fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
const buf = Buffer.from(await res.arrayBuffer());
fs.writeFileSync(out, buf);
const stabilityLabel =
  Object.entries(PRESETS).find(([, v]) => v === stability)?.[0] ?? String(stability);
console.log(
  JSON.stringify({
    ok: true,
    out,
    bytes: buf.length,
    provider: "elevenlabs",
    voiceId,
    modelId,
    stability: stabilityLabel,
    chars: text.length,
    format,
  })
);
