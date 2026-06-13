#!/usr/bin/env node
// Generate background music with the Suno API (sunoapi.org). Async: it submits a job, polls
// record-info until SUCCESS, then downloads the finished track.
// Docs: https://docs.sunoapi.org/suno-api/quickstart
//
// Usage:
//   node generate-music-suno.mjs --prompt "calm lofi tech bed" --instrumental --out public/music.mp3 \
//        [--model V4_5] [--style "lofi, ambient"] [--title "Bed"] [--custom] [--max-wait 240]
//
// Models: V3_5, V4, V4_5, V4_5PLUS, V5 (default V4_5). customMode requires --style and --title.
import fs from "node:fs";
import path from "node:path";
import { getSunoKey, parseArgs, die, sleep } from "./_shared.mjs";

const args = parseArgs(process.argv.slice(2));
let prompt = args.prompt;
if (args["prompt-file"]) prompt = fs.readFileSync(args["prompt-file"], "utf8");
if (!prompt || !prompt.trim()) die("Provide --prompt or --prompt-file");

const BASE = "https://api.sunoapi.org";
const key = getSunoKey();
const out = args.out || "music.mp3";
const maxWaitMs = (args["max-wait"] != null ? Number(args["max-wait"]) : 240) * 1000;

const body = {
  prompt: prompt.trim(),
  model: args.model || "V4_5",
  customMode: Boolean(args.custom),
  instrumental: Boolean(args.instrumental),
  // We poll record-info, but the API expects a callback URL field; a placeholder is fine.
  callBackUrl: args["callback-url"] || "https://example.com/callback",
};
if (args.custom) {
  if (!args.style || !args.title) die("customMode (--custom) requires --style and --title");
  body.style = String(args.style);
  body.title = String(args.title);
}

const headers = { Authorization: `Bearer ${key}`, "Content-Type": "application/json" };

const genRes = await fetch(`${BASE}/api/v1/generate`, { method: "POST", headers, body: JSON.stringify(body) });
const genJson = await genRes.json().catch(() => ({}));
if (!genRes.ok || (genJson.code && genJson.code !== 200)) {
  die(`Suno generate failed (${genRes.status}): ${JSON.stringify(genJson)}`);
}
const taskId = genJson.data?.taskId || genJson.data?.task_id || genJson.taskId;
if (!taskId) die(`No taskId returned: ${JSON.stringify(genJson)}`);
console.error(`Suno taskId=${taskId} — polling…`);

function findAudioUrl(rec) {
  const r = rec?.response || rec?.data?.response || {};
  const arr = r.sunoData || r.data || r.clips || [];
  for (const c of arr) {
    const u = c.audioUrl || c.audio_url || c.streamAudioUrl || c.stream_audio_url;
    if (u) return u;
  }
  return null;
}

const started = Date.now();
let audioUrl = null;
while (Date.now() - started < maxWaitMs) {
  await sleep(8000);
  const r = await fetch(`${BASE}/api/v1/generate/record-info?taskId=${encodeURIComponent(taskId)}`, { headers });
  const j = await r.json().catch(() => ({}));
  const rec = j.data || {};
  const status = rec.status || rec.state;
  if (status === "SUCCESS" || status === "complete" || status === "FIRST_SUCCESS") {
    audioUrl = findAudioUrl(rec);
    if (audioUrl) break;
  }
  if (status === "FAILED" || status === "error" || rec.errorCode) {
    die(`Suno generation failed: ${JSON.stringify(j)}`);
  }
  console.error(`  …status=${status || "?"} (${Math.round((Date.now() - started) / 1000)}s)`);
}
if (!audioUrl) die("Timed out waiting for Suno (increase --max-wait).");

// download the finished track
const dl = await fetch(audioUrl);
if (!dl.ok) die(`Failed to download audio (${dl.status})`);
fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
const buf = Buffer.from(await dl.arrayBuffer());
fs.writeFileSync(out, buf);
console.log(JSON.stringify({ ok: true, out, bytes: buf.length, provider: "suno", taskId, audioUrl }));
