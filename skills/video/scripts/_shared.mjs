// Shared helpers for the /video skill scripts. Zero external dependencies (Node 18+).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url)); // <skill>/scripts
const SKILL_DIR = path.resolve(SCRIPT_DIR, ".."); // <skill>
const SKILLS_DIR = path.resolve(SKILL_DIR, ".."); // parent of all skills (e.g. ~/.claude/skills)

function readEnvFile(p) {
  const out = {};
  if (p && fs.existsSync(p)) {
    const txt = fs.readFileSync(p, "utf8");
    for (const line of txt.split(/\r?\n/)) {
      if (/^\s*#/.test(line)) continue;
      const m = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$/);
      if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "").trim();
    }
  }
  return out;
}

// .env files to search, in order (first hit wins per key).
// Override with VIDEO_ENV_FILE / SKILL_ENV_FILE to point at any .env.
function envFiles() {
  const list = [];
  if (process.env.VIDEO_ENV_FILE) list.push(process.env.VIDEO_ENV_FILE);
  if (process.env.SKILL_ENV_FILE) list.push(process.env.SKILL_ENV_FILE);
  list.push(path.join(SKILL_DIR, ".env")); // skill-local .env
  list.push(path.join(SKILLS_DIR, ".env")); // shared .env next to the skills folder
  list.push(path.join(os.homedir(), ".claude", ".env")); // user-global Claude .env
  list.push(path.join(os.homedir(), "Documents", ".env")); // legacy fallback
  return list;
}

// Load the creator persona/config (voice id, name, links, accent, presenter...).
// Override path with VIDEO_PERSONA_FILE. Falls back to the example template.
export function loadPersona() {
  const candidates = [];
  if (process.env.VIDEO_PERSONA_FILE) candidates.push(process.env.VIDEO_PERSONA_FILE);
  candidates.push(path.join(SKILL_DIR, "config", "persona.json"));
  candidates.push(path.join(SKILLS_DIR, "config", "persona.json"));
  candidates.push(path.join(SKILL_DIR, "config", "persona.example.json"));
  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) return JSON.parse(fs.readFileSync(p, "utf8"));
    } catch {
      /* ignore malformed file, try next */
    }
  }
  return {};
}

/**
 * Resolve an API key. Names are in PRIORITY order: for each name we check the
 * env var, then the .env file(s), before moving to the next name. This way the
 * canonical name (e.g. ELEVEN_LABS in your .env) beats a stale legacy
 * env var (e.g. an old ELEVENLABS_API_KEY left in the user environment).
 */
export function getKey(envNames, label) {
  const files = envFiles().map(readEnvFile);
  for (const n of envNames) {
    if (process.env[n] && process.env[n].trim()) return process.env[n].trim();
    for (const e of files) if (e[n]) return e[n];
  }
  throw new Error(
    `No ${label} API key found. Set ${envNames[0]} in the environment, or add it to your .env ` +
      `(point VIDEO_ENV_FILE at that file).`
  );
}

export const getApiKey = () => getKey(["OPENAI_API_KEY"], "OpenAI"); // back-compat
export const getOpenAIKey = () => getKey(["OPENAI_API_KEY"], "OpenAI");
export const getElevenLabsKey = () =>
  getKey(["ELEVEN_LABS", "ELEVENLABS_API_KEY", "ELEVEN_API_KEY", "XI_API_KEY"], "ElevenLabs");
export const getSunoKey = () => getKey(["SUNO_API_KEY", "SUNO_API"], "Suno");
export const getOpenRouterKey = () =>
  getKey(["OPENROUTER_API", "OPENROUTER_API_KEY", "OPENROUTER_KEY"], "OpenRouter");

/** Minimal --flag value / --flag=value parser. Returns a plain object. */
export function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2);
    if (key.includes("=")) {
      const [k, ...rest] = key.split("=");
      out[k] = rest.join("=");
    } else if (i + 1 < argv.length && !argv[i + 1].startsWith("--")) {
      out[key] = argv[++i];
    } else {
      out[key] = true;
    }
  }
  return out;
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function die(msg) {
  console.error("ERROR: " + msg);
  process.exit(1);
}
