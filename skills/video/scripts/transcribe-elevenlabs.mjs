#!/usr/bin/env node
// Transcribe audio to WORD-LEVEL timestamps with ElevenLabs Scribe (alternative to whisper-1).
// Outputs the SAME @remotion/captions Caption[] shape as transcribe-timestamps.mjs, so it's a
// drop-in replacement for the captions step.
//
// Usage:
//   node transcribe-elevenlabs.mjs --audio public/voice.mp3 --out public/captions.json \
//        [--model-id scribe_v1] [--language en]
//
// Models: scribe_v1 (default), scribe_v2. Returns words with start/end seconds.
import fs from "node:fs";
import path from "node:path";
import { getElevenLabsKey, parseArgs, die } from "./_shared.mjs";

const args = parseArgs(process.argv.slice(2));
const audio = args.audio;
const out = args.out || "captions.json";
const modelId = args["model-id"] || "scribe_v1";
if (!audio || !fs.existsSync(audio)) die("Provide a valid --audio path");

const form = new FormData();
form.append("file", new Blob([fs.readFileSync(audio)]), path.basename(audio));
form.append("model_id", modelId);
form.append("timestamps_granularity", "word");
if (args.language) form.append("language_code", String(args.language));

const res = await fetch("https://api.elevenlabs.io/v1/speech-to-text", {
  method: "POST",
  headers: { "xi-api-key": getElevenLabsKey() },
  body: form,
});
if (!res.ok) die(`ElevenLabs STT failed (${res.status}): ${await res.text()}`);

const data = await res.json();
const words = (data.words || []).filter((w) => w.type === "word" && w.start != null);
if (!words.length) die("No word timestamps returned.");

const captions = words.map((w) => {
  const startMs = Math.round((w.start ?? 0) * 1000);
  const endMs = Math.round((w.end ?? w.start ?? 0) * 1000);
  return {
    text: " " + String(w.text).trim(), // leading space required by @remotion/captions
    startMs,
    endMs,
    timestampMs: Math.round((startMs + endMs) / 2),
    confidence: w.logprob != null ? Math.exp(w.logprob) : null,
  };
});

fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
fs.writeFileSync(out, JSON.stringify(captions, null, 2));
console.log(
  JSON.stringify({ ok: true, out, words: captions.length, durationSec: (captions.at(-1)?.endMs ?? 0) / 1000, provider: "elevenlabs", modelId })
);
