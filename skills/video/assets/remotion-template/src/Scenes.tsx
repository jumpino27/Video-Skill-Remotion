import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { type Caption } from "@remotion/captions";
import { useSceneCuts } from "./scene-sync";

/**
 * Animated SVG scenes that illustrate the narration as it plays.
 * Text (kickers, the typed prompt, project subtitles, the CTA) is localized via
 * the `lang` prop so the same animation works for every language version.
 * Coordinate space for every scene SVG is 1080 x 1920 (the video frame).
 */

const VW = 1080;
const VH = 1920;
const CX = VW / 2;

export type Lang = "en" | "de" | "it" | "ro";

type L10n = {
  kickers: [string, string, string, string, string, string];
  typed: string;
  subs: [string, string, string];
  cta: string;
};

export const L10N: Record<Lang, L10n> = {
  en: {
    kickers: [
      "DESCRIBE IT",
      "AI SYSTEMS ARCHITECT",
      "AGENTS · SERVERS · ZERO-TOUCH",
      "SHIPPED",
      "IT JUST WORKS",
      "",
    ],
    typed: "describe what you want…",
    subs: ["first project", "second project", "third project"],
    cta: "Let's build it →",
  },
  de: {
    kickers: [
      "BESCHREIB ES",
      "KI-SYSTEMARCHITEKT",
      "AGENTEN · SERVER · ZERO-TOUCH",
      "VERÖFFENTLICHT",
      "ES LÄUFT EINFACH",
      "",
    ],
    typed: "beschreibe, was du willst…",
    subs: ["erstes Projekt", "zweites Projekt", "drittes Projekt"],
    cta: "Lass es uns bauen →",
  },
  it: {
    kickers: [
      "DESCRIVILO",
      "ARCHITETTO DI SISTEMI AI",
      "AGENTI · SERVER · ZERO-TOUCH",
      "PUBBLICATO",
      "FUNZIONA E BASTA",
      "",
    ],
    typed: "descrivi ciò che vuoi…",
    subs: ["primo progetto", "secondo progetto", "terzo progetto"],
    cta: "Costruiamolo →",
  },
  ro: {
    kickers: [
      "DESCRIE-L",
      "ARHITECT DE SISTEME AI",
      "AGENȚI · SERVERE · ZERO-TOUCH",
      "LANSAT",
      "FUNCȚIONEAZĂ PUR ȘI SIMPLU",
      "",
    ],
    typed: "descrie ce vrei…",
    subs: ["primul proiect", "al doilea proiect", "al treilea proiect"],
    cta: "Hai să-l construim →",
  },
};

type SceneProps = { accent: string; len: number; l10n: L10n };

// ---------- shared animation helpers ----------
function useInOut(len: number) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const appear = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 14 });
  const disappear = interpolate(frame, [len - 12, len], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return { frame, fps, opacity: appear * disappear, appear };
}

const Kicker: React.FC<{ text: string; accent: string; appear: number }> = ({
  text,
  accent,
  appear,
}) => {
  if (!text) return null;
  return (
    <div
      style={{
        position: "absolute",
        top: "12%",
        left: 0,
        right: 0,
        textAlign: "center",
        padding: "0 6%",
        fontFamily: "'Inter','Helvetica Neue',Arial,system-ui,sans-serif",
        fontWeight: 800,
        letterSpacing: "3px",
        fontSize: 30,
        color: accent,
        opacity: appear,
        textShadow: `0 0 22px ${accent}88`,
        transform: `translateY(${(1 - appear) * -20}px)`,
      }}
    >
      {text}
    </div>
  );
};

const SceneFrame: React.FC<{
  kicker: string;
  accent: string;
  len: number;
  children: React.ReactNode;
}> = ({ kicker, accent, len, children }) => {
  const { opacity, appear } = useInOut(len);
  return (
    <AbsoluteFill style={{ opacity }}>
      <Kicker text={kicker} accent={accent} appear={appear} />
      {children}
    </AbsoluteFill>
  );
};

const Svg: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg
    width={VW}
    height={VH}
    viewBox={`0 0 ${VW} ${VH}`}
    style={{ position: "absolute", inset: 0 }}
  >
    {children}
  </svg>
);

const Defs: React.FC<{ accent: string }> = ({ accent }) => (
  <defs>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="10" result="b" />
      <feMerge>
        <feMergeNode in="b" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <radialGradient id="hubgrad">
      <stop offset="0%" stopColor={accent} stopOpacity="0.9" />
      <stop offset="100%" stopColor={accent} stopOpacity="0.15" />
    </radialGradient>
  </defs>
);

// ============================================================
// SCENE 1 — Intent → Self-running system
// ============================================================
const SceneIntent: React.FC<SceneProps> = ({ accent, l10n }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const boxY = 620;
  const sysY = 1080;

  const full = l10n.typed;
  const chars = Math.floor(
    interpolate(frame, [10, 55], [0, full.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );
  const typed = full.slice(0, chars);
  const cursorOn = Math.floor(frame / 15) % 2 === 0;

  const travel = interpolate(frame, [55, 80], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const packY = boxY + 110 + travel * (sysY - boxY - 200);
  const spin = (frame / fps) * 120;
  const sysGlow = interpolate(frame, [70, 95], [0.2, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <Svg>
      <Defs accent={accent} />
      <g>
        <rect
          x={CX - 380}
          y={boxY}
          width={760}
          height={170}
          rx={26}
          fill="#11131c"
          stroke={accent}
          strokeWidth={3}
          filter="url(#glow)"
        />
        <text
          x={CX - 340}
          y={boxY + 102}
          fontFamily="ui-monospace, 'SF Mono', Menlo, monospace"
          fontSize={36}
          fill="#e8eefc"
        >
          {typed}
          <tspan fill={accent}>{cursorOn ? "▌" : " "}</tspan>
        </text>
      </g>

      <line
        x1={CX}
        y1={boxY + 170}
        x2={CX}
        y2={sysY - 130}
        stroke={`${accent}55`}
        strokeWidth={4}
        strokeDasharray="2 14"
        strokeLinecap="round"
      />
      {travel > 0 && travel < 1 && (
        <circle cx={CX} cy={packY} r={12} fill={accent} filter="url(#glow)" />
      )}

      <g transform={`translate(${CX} ${sysY})`} opacity={sysGlow}>
        <circle r={150} fill="url(#hubgrad)" filter="url(#glow)" />
        <g transform={`rotate(${spin})`} stroke={accent} strokeWidth={10} fill="none">
          <circle r={86} />
          {Array.from({ length: 8 }).map((_, i) => {
            const a = (i / 8) * Math.PI * 2;
            return (
              <line
                key={i}
                x1={Math.cos(a) * 86}
                y1={Math.sin(a) * 86}
                x2={Math.cos(a) * 118}
                y2={Math.sin(a) * 118}
              />
            );
          })}
          <circle r={34} fill={accent} stroke="none" />
        </g>
      </g>
    </Svg>
  );
};

// ============================================================
// SCENE 2 — Architect (blueprint)
// ============================================================
const SceneArchitect: React.FC<SceneProps> = ({ accent }) => {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [4, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const cy = 900;
  const R = 230;
  const pts = Array.from({ length: 6 }).map((_, i) => {
    const a = (i / 6) * Math.PI * 2 - Math.PI / 2;
    return [CX + Math.cos(a) * R, cy + Math.sin(a) * R];
  });
  const perimeter = R * 6;
  return (
    <Svg>
      <Defs accent={accent} />
      <g stroke={`${accent}22`} strokeWidth={1.5}>
        {Array.from({ length: 12 }).map((_, i) => (
          <line key={"v" + i} x1={i * 96} y1={400} x2={i * 96} y2={1400} opacity={draw} />
        ))}
        {Array.from({ length: 11 }).map((_, i) => (
          <line key={"h" + i} x1={60} y1={400 + i * 100} x2={1020} y2={400 + i * 100} opacity={draw} />
        ))}
      </g>
      <polygon
        points={pts.map((p) => p.join(",")).join(" ")}
        fill={`${accent}10`}
        stroke={accent}
        strokeWidth={6}
        strokeDasharray={perimeter}
        strokeDashoffset={perimeter * (1 - draw)}
        filter="url(#glow)"
      />
      <g transform={`translate(${CX} ${cy})`} stroke={accent} strokeWidth={8} fill="none" opacity={draw}>
        <line x1={0} y1={-90} x2={-70} y2={90} />
        <line x1={0} y1={-90} x2={70} y2={90} />
        <circle cx={0} cy={-90} r={14} fill={accent} stroke="none" />
        <line x1={-46} y1={42} x2={46} y2={42} />
      </g>
    </Svg>
  );
};

// ============================================================
// SCENE 3 — Orchestration hub: agents + servers + zero-touch
// ============================================================
const SceneOrchestrate: React.FC<SceneProps> = ({ accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hub = { x: CX, y: 760 };
  const R = 300;
  const n = 6;
  const rot = (frame / fps) * 18;
  const agents = Array.from({ length: n }).map((_, i) => {
    const a = (i / n) * Math.PI * 2 + (rot * Math.PI) / 180;
    return { x: hub.x + Math.cos(a) * R, y: hub.y + Math.sin(a) * R, i };
  });
  const gearSpin = (frame / fps) * 90;

  return (
    <Svg>
      <Defs accent={accent} />
      {agents.map((ag) => {
        const t = ((frame + ag.i * 9) % 40) / 40;
        const px = hub.x + (ag.x - hub.x) * t;
        const py = hub.y + (ag.y - hub.y) * t;
        return (
          <g key={ag.i}>
            <line x1={hub.x} y1={hub.y} x2={ag.x} y2={ag.y} stroke={`${accent}40`} strokeWidth={3} />
            <circle cx={px} cy={py} r={7} fill={accent} />
            <circle cx={ag.x} cy={ag.y} r={34} fill="#11131c" stroke={accent} strokeWidth={4} filter="url(#glow)" />
            <circle cx={ag.x} cy={ag.y} r={12} fill={accent} />
          </g>
        );
      })}
      <circle cx={hub.x} cy={hub.y} r={92} fill="url(#hubgrad)" filter="url(#glow)" />
      <circle cx={hub.x} cy={hub.y} r={58} fill="#0c0c12" stroke={accent} strokeWidth={5} />
      <text x={hub.x} y={hub.y + 12} textAnchor="middle" fontFamily="Inter,system-ui,sans-serif" fontWeight={800} fontSize={34} fill={accent}>
        AI
      </text>

      <g transform={`translate(${CX - 170} 1180)`}>
        {[0, 1, 2].map((r) => {
          const on = Math.floor(frame / 8 + r) % 2 === 0;
          return (
            <g key={r} transform={`translate(0 ${r * 78})`}>
              <rect x={0} y={0} width={340} height={62} rx={10} fill="#13151f" stroke={`${accent}66`} strokeWidth={2.5} />
              <circle cx={32} cy={31} r={9} fill={on ? accent : `${accent}33`} filter={on ? "url(#glow)" : undefined} />
              <circle cx={62} cy={31} r={9} fill={!on ? accent : `${accent}33`} />
              <rect x={120} y={22} width={180} height={8} rx={4} fill={`${accent}55`} />
            </g>
          );
        })}
      </g>

      <g transform={`translate(${CX + 250} 1290) rotate(${gearSpin})`} stroke={accent} strokeWidth={8} fill="none">
        <circle r={52} />
        {Array.from({ length: 8 }).map((_, i) => {
          const a = (i / 8) * Math.PI * 2;
          return <line key={i} x1={Math.cos(a) * 52} y1={Math.sin(a) * 52} x2={Math.cos(a) * 74} y2={Math.sin(a) * 74} />;
        })}
        <circle r={18} fill={accent} stroke="none" />
      </g>
    </Svg>
  );
};

// ============================================================
// SCENE 4 — Projects shipped
// ============================================================
const SceneProjects: React.FC<SceneProps> = ({ accent, l10n }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Placeholder items — the skill rewrites Scenes.tsx per video.
  const items = [
    { label: "Project One", sub: l10n.subs[0] },
    { label: "Project Two", sub: l10n.subs[1] },
    { label: "Project Three", sub: l10n.subs[2] },
  ];
  return (
    <Svg>
      <Defs accent={accent} />
      {items.map((it, i) => {
        const s = spring({ frame: frame - 6 - i * 10, fps, config: { damping: 200 }, durationInFrames: 16 });
        const y = 620 + i * 250;
        const x = CX - 380;
        return (
          <g key={i} transform={`translate(${x} ${y})`} opacity={s}>
            <g transform={`translate(${(1 - s) * 60} 0)`}>
              <rect width={760} height={190} rx={24} fill="#11131c" stroke={`${accent}99`} strokeWidth={3} filter="url(#glow)" />
              <rect x={28} y={30} width={130} height={130} rx={20} fill={`${accent}22`} stroke={accent} strokeWidth={3} />
              {i === 0 && <polygon points="78,70 78,150 138,110" transform="translate(8 -10)" fill={accent} />}
              {i === 1 && (
                <g transform="translate(93 60)" fill={accent}>
                  <path d="M0 0 C-40 0 -40 50 0 90 C40 50 40 0 0 0 Z" />
                  <circle cx={0} cy={32} r={14} fill="#11131c" />
                </g>
              )}
              {i === 2 && (
                <g transform="translate(50 78)" fill="none" stroke={accent} strokeWidth={8}>
                  <rect x={0} y={0} width={86} height={56} rx={28} />
                  <line x1={22} y1={28} x2={40} y2={28} />
                  <line x1={31} y1={19} x2={31} y2={37} />
                  <circle cx={64} cy={24} r={5} fill={accent} />
                  <circle cx={74} cy={34} r={5} fill={accent} />
                </g>
              )}
              <text x={195} y={92} fontFamily="Inter,system-ui,sans-serif" fontWeight={800} fontSize={44} fill="#eef3ff">
                {it.label}
              </text>
              <text x={195} y={140} fontFamily="Inter,system-ui,sans-serif" fontWeight={500} fontSize={30} fill={`${accent}cc`}>
                {it.sub}
              </text>
            </g>
          </g>
        );
      })}
    </Svg>
  );
};

// ============================================================
// SCENE 5 — Idea → system that just works
// ============================================================
const SceneWorks: React.FC<SceneProps> = ({ accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const y = 900;
  const gearSpin = (frame / fps) * 120;
  const check = interpolate(frame, [42, 70], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const bulb = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 14 });
  const arrow1 = interpolate(frame, [16, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const arrow2 = interpolate(frame, [34, 48], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const checkLen = 150;
  return (
    <Svg>
      <Defs accent={accent} />
      <g transform={`translate(${CX - 320} ${y})`} opacity={bulb} stroke={accent} strokeWidth={8} fill="none">
        <circle r={62} fill={`${accent}22`} />
        <path d="M0 -28 a28 28 0 1 1 -0.1 0" />
        <line x1={-16} y1={44} x2={16} y2={44} />
        <line x1={-12} y1={60} x2={12} y2={60} />
      </g>
      <line x1={CX - 230} y1={y} x2={CX - 80} y2={y} stroke={accent} strokeWidth={6} strokeDasharray={160} strokeDashoffset={160 * (1 - arrow1)} />
      <g transform={`translate(${CX} ${y}) rotate(${gearSpin})`} stroke={accent} strokeWidth={8} fill="none" opacity={arrow1}>
        <circle r={56} />
        {Array.from({ length: 8 }).map((_, i) => {
          const a = (i / 8) * Math.PI * 2;
          return <line key={i} x1={Math.cos(a) * 56} y1={Math.sin(a) * 56} x2={Math.cos(a) * 78} y2={Math.sin(a) * 78} />;
        })}
        <circle r={18} fill={accent} stroke="none" />
      </g>
      <line x1={CX + 90} y1={y} x2={CX + 240} y2={y} stroke={accent} strokeWidth={6} strokeDasharray={160} strokeDashoffset={160 * (1 - arrow2)} />
      <g transform={`translate(${CX + 320} ${y})`}>
        <circle r={64} fill={`${accent}22`} stroke={accent} strokeWidth={6} opacity={arrow2} />
        <path
          d="M -28 2 L -6 26 L 32 -22"
          fill="none"
          stroke={accent}
          strokeWidth={12}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={checkLen}
          strokeDashoffset={checkLen * (1 - check)}
          filter="url(#glow)"
        />
      </g>
    </Svg>
  );
};

// ============================================================
// SCENE 6 — CTA: yourbrand.com (placeholder — set from your persona/brand)
// ============================================================
const SceneCTA: React.FC<SceneProps> = ({ accent, l10n }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 18 });
  const underline = interpolate(frame, [16, 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pulse = 0.5 + 0.5 * Math.sin((frame / fps) * 4);
  return (
    <Svg>
      <Defs accent={accent} />
      <g transform={`translate(0 ${-40})`}>
        <text
          x={CX}
          y={840}
          textAnchor="middle"
          fontFamily="Inter,system-ui,sans-serif"
          fontWeight={900}
          fontSize={84}
          fill="#ffffff"
          opacity={s}
          transform={`translate(0 ${(1 - s) * 30})`}
          filter="url(#glow)"
        >
          yourbrand
          <tspan fill={accent}>.com</tspan>
        </text>
        <rect x={CX - 360} y={880} width={720 * underline} height={8} rx={4} fill={accent} filter="url(#glow)" />
        <g opacity={s}>
          <rect
            x={CX - 280}
            y={980}
            width={560}
            height={112}
            rx={56}
            fill="none"
            stroke={accent}
            strokeWidth={4}
            opacity={0.5 + 0.5 * pulse}
            filter="url(#glow)"
          />
          <text x={CX} y={1052} textAnchor="middle" fontFamily="Inter,system-ui,sans-serif" fontWeight={800} fontSize={40} fill={accent}>
            {l10n.cta}
          </text>
        </g>
      </g>
    </Svg>
  );
};

// ============================================================
// Scene timeline (weights ≈ sentence durations of the ~32s script)
// ============================================================
const SCENE_COMPS: React.FC<SceneProps>[] = [
  SceneIntent,
  SceneArchitect,
  SceneOrchestrate,
  SceneProjects,
  SceneWorks,
  SceneCTA,
];
const WEIGHTS = [6, 4, 9, 4, 4, 6];

export const Scenes: React.FC<{ accent: string; lang?: Lang; captions?: Caption[] }> = ({
  accent,
  lang = "en",
  captions,
}) => {
  void WEIGHTS;
  const l10n = L10N[lang] ?? L10N.en;
  // Scene cuts are SYNCED to the narration's pauses (sentence boundaries), so each
  // scene lands while its matching sentence is spoken. Falls back to equal slices.
  const cuts = useSceneCuts(captions, SCENE_COMPS.length);
  return (
    <AbsoluteFill>
      {SCENE_COMPS.map((Comp, i) => {
        const { from, len } = cuts[i];
        const kicker = l10n.kickers[i];
        return (
          <Sequence key={i} from={from} durationInFrames={len} name={kicker || "CTA"}>
            <SceneFrame kicker={kicker} accent={accent} len={len}>
              <Comp accent={accent} len={len} l10n={l10n} />
            </SceneFrame>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
