import React from 'react';
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from 'remotion';
import { clamp, lerp } from './anim';
import { KitDefs } from './kit';
import { SetDefs } from './light';

// The episode engine. An episode is a set of shots plus a timeline (written by scripts/plan.py from the voice's word
// timings). Each shot is a pure function of its own clock t, so the edit can cut back to a shot, hold it, or play it
// backwards: a segment just says which stretch of the shot's clock it shows.

export type Seg = {
  shot: string; // shot id (S1, S2...)
  a: number; // first global frame
  b: number; // first frame after it
  t0: number; // the shot's clock at a
  t1: number; // the shot's clock at b (smaller than t0 when the segment plays backwards)
  look?: string; // a named power look (rewind, freeze...) the episode defines: grade + overlay while it runs
  line?: string; // the words spoken over it (for the storyboard)
};
export type ShotInfo = { id: string; size: string; key: number; len: number; first: number; line?: string; note?: string };
export type Fx = { f: number; kind: 'flash' | 'shake'; color?: string; o?: number; len?: number; amp?: number };
export type Timeline = {
  slug: string;
  title: string;
  fps: number;
  total: number;
  segments: Seg[];
  shots: ShotInfo[];
  fx: Fx[];
  audio: { voice?: string; sfx?: string; music?: string; voiceVol?: number; sfxVol?: number; musicVol?: number };
};

/** What every shot receives: its own clock t, how long its clock runs (len), and the global frame f. */
export type ShotProps = { t: number; len: number; f: number };
export type ShotMap = Record<string, React.FC<ShotProps>>;

/** A power look: a CSS grade on the picture and an overlay on top while segments with this look run. */
export type LookDef = {
  grade?: (lv: number) => string;
  jitter?: number; // sideways picture jitter in px at full strength
  Overlay?: React.FC<{ f: number; lv: number; p: number; n: number }>; // p: progress through this run, n: which run (0, 1, 2...)
};

const segAt = (tl: Timeline, f: number) => tl.segments.find((s) => f >= s.a && f < s.b) ?? tl.segments[tl.segments.length - 1];
const clockAt = (s: Seg, f: number) => (s.t1 - s.t0 === s.b - s.a ? s.t0 + (f - s.a) : lerp(s.t0, s.t1, (f - s.a) / (s.b - s.a)));

/** Runs of neighbouring segments sharing a look, so a look spanning two shots doesn't blink at the cut. */
const lookRuns = (tl: Timeline) => {
  const runs: { look: string; a: number; b: number; n: number }[] = [];
  const count: Record<string, number> = {};
  for (const s of tl.segments) {
    if (!s.look) continue;
    const last = runs[runs.length - 1];
    if (last && last.look === s.look && last.b === s.a) last.b = s.b;
    else {
      runs.push({ look: s.look, a: s.a, b: s.b, n: count[s.look] ?? 0 });
      count[s.look] = (count[s.look] ?? 0) + 1;
    }
  }
  return runs;
};

const fxAt = (tl: Timeline, f: number) => {
  let flash: { color: string; o: number } | null = null;
  let x = 0;
  let y = 0;
  for (const e of tl.fx) {
    if (e.kind === 'flash') {
      if (f === e.f) flash = { color: e.color ?? '#FFFFFF', o: e.o ?? 0.85 };
      else if (f === e.f + 1) flash = { color: e.color ?? '#FFFFFF', o: (e.o ?? 0.85) * 0.35 };
    } else if (e.kind === 'shake') {
      const len = e.len ?? 8;
      const amp = e.amp ?? 12;
      if (f >= e.f && f < e.f + len) {
        const k = amp * (1 - (f - e.f) / len);
        x += Math.sin(f * 2.9) * k;
        y += Math.cos(f * 3.7) * k * 0.7;
      }
    }
  }
  return { flash, x, y };
};

/** Vignette and a fine grain that changes on twos, to take the vector edge off (the genre's finish). */
const Grade: React.FC<{ f: number; grain: boolean; vignette: boolean }> = ({ f, grain, vignette }) => (
  <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
    <defs>
      <radialGradient id="epVig" cx="50%" cy="50%" r="75%">
        <stop offset="55%" stopColor="#000" stopOpacity={0} />
        <stop offset="100%" stopColor="#000" stopOpacity={0.55} />
      </radialGradient>
      <filter id="epGrain" x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.floor(f / 2) % 97} />
        <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.06 0" />
      </filter>
    </defs>
    {vignette ? <rect width="1920" height="1080" fill="url(#epVig)" /> : null}
    {grain ? <rect width="1920" height="1080" filter="url(#epGrain)" /> : null}
  </svg>
);

/** One shot drawn in the shared defs (filters, gradients), in a 1920 x 1080 world. */
export const ShotFrame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg width={1920} height={1080} viewBox="0 0 1920 1080">
    <KitDefs />
    <SetDefs />
    {children}
  </svg>
);

/**
 * How a shot is reframed for a vertical (9:16) cut. Crop: a 9:16 window of the 16:9 world, centred on (cx, cy), `w` world
 * units wide (608 shows the full height). Fit: the whole 16:9 frame in the middle, the same shot blurred behind it (titles,
 * schematics, anything wide).
 */
/** The 9:16 window on a 16:9 shot: centre (cx, cy) and width w in 1920 x 1080 units (608 = full height, no bars),
 *  panning to cx2 between the fractions span[0] and span[1] of the shot.
 *  fit: a sharp full-height band of the frame (x from cx - w/2 to cx + w/2, the whole width by default) over its own blur. */
export type Reframe = { cx?: number; cy?: number; w?: number; fit?: boolean; cx2?: number; span?: [number, number] };
export type EpisodeProps = { timeline: Timeline; shots: ShotMap; looks?: Record<string, LookDef>; grain?: boolean; vignette?: boolean; bg?: string; vertical?: Record<string, Reframe> };

export const Episode: React.FC<EpisodeProps> = ({ timeline: tl, shots, looks = {}, grain = true, vignette = true, bg = '#0E0C1E' }) => {
  const f = useCurrentFrame();
  const seg = segAt(tl, f);
  const Shot = shots[seg.shot];
  const info = tl.shots.find((s) => s.id === seg.shot);
  const run = lookRuns(tl).find((r) => f >= r.a && f < r.b);
  const def = run ? looks[run.look] : undefined;
  const lv = run ? Math.min(clamp((f - run.a + 1) / 2), clamp((run.b - f) / 2)) : 0;
  const jitter = def?.jitter && lv > 0 ? Math.sin(f * 13.7) * def.jitter * lv : 0;
  const { flash, x, y } = fxAt(tl, f);
  const A = tl.audio;
  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <AbsoluteFill style={{ transform: `translate(${x + jitter}px, ${y}px) scale(${x || y ? 1.02 : 1})`, filter: def?.grade && lv > 0 ? def.grade(lv) : undefined }}>
        <ShotFrame>{Shot ? <Shot t={clockAt(seg, f)} len={info?.len ?? seg.b - seg.a} f={f} /> : null}</ShotFrame>
      </AbsoluteFill>
      <Grade f={f} grain={grain} vignette={vignette} />
      {def?.Overlay && run ? (
        <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0, opacity: lv }}>
          <def.Overlay f={f} lv={lv} p={clamp((f - run.a) / (run.b - run.a))} n={run.n} />
        </svg>
      ) : null}
      {flash ? <AbsoluteFill style={{ backgroundColor: flash.color, opacity: flash.o }} /> : null}
      {A.voice ? <Audio src={staticFile(A.voice)} volume={A.voiceVol ?? 1} /> : null}
      {A.sfx ? <Audio src={staticFile(A.sfx)} volume={A.sfxVol ?? 1} /> : null}
      {A.music ? <Audio src={staticFile(A.music)} volume={A.musicVol ?? 1} /> : null}
    </AbsoluteFill>
  );
};

/** The storyboard: frame i is shot i at its key frame, no audio, no look. Render it with scripts/stills.mjs. */
export const Board: React.FC<{ timeline: Timeline; shots: ShotMap; grain?: boolean; vignette?: boolean; bg?: string }> = ({ timeline: tl, shots, grain = true, vignette = true, bg = '#0E0C1E' }) => {
  const f = useCurrentFrame();
  const info = tl.shots[Math.min(f, tl.shots.length - 1)];
  const Shot = shots[info.id];
  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <ShotFrame>{Shot ? <Shot t={info.key} len={info.len} f={info.first + info.key} /> : null}</ShotFrame>
      <Grade f={info.key} grain={grain} vignette={vignette} />
    </AbsoluteFill>
  );
};


// ---------------------------------------------------------------- the vertical cut (9:16, 1080 x 1920)
const VW = 1080;
const VH = 1920;

const VGrade: React.FC<{ f: number; grain: boolean; vignette: boolean }> = ({ f, grain, vignette }) => (
  <svg width={VW} height={VH} viewBox={`0 0 ${VW} ${VH}`} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
    <defs>
      <radialGradient id="vVig" cx="50%" cy="50%" r="75%">
        <stop offset="55%" stopColor="#000" stopOpacity={0} />
        <stop offset="100%" stopColor="#000" stopOpacity={0.55} />
      </radialGradient>
      <filter id="vGrain" x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.floor(f / 2) % 97} />
        <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.06 0" />
      </filter>
    </defs>
    {vignette ? <rect width={VW} height={VH} fill="url(#vVig)" /> : null}
    {grain ? <rect width={VW} height={VH} filter="url(#vGrain)" /> : null}
  </svg>
);

/** One shot drawn through a 9:16 window of the world. */
const VShot: React.FC<{ r: Reframe; p?: number; children: React.ReactNode; blur?: number }> = ({ r, p = 0, children, blur = 0 }) => {
  const w = r.w ?? 608;
  const h = (w * VH) / VW;
  const [a, b] = r.span ?? [0, 1];
  const k = clamp((p - a) / Math.max(1e-6, b - a));
  const e = k * k * (3 - 2 * k);
  const cx = r.cx2 === undefined ? r.cx ?? 960 : (r.cx ?? 960) + (r.cx2 - (r.cx ?? 960)) * e;
  const cy = r.cy ?? 540;
  return (
    <svg width={VW} height={VH} viewBox={`${cx - w / 2} ${cy - h / 2} ${w} ${h}`} preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, filter: blur ? `blur(${blur}px) brightness(0.55)` : undefined }}>
      <KitDefs />
      <SetDefs />
      {children}
    </svg>
  );
};

export const VerticalEpisode: React.FC<EpisodeProps> = ({ timeline: tl, shots, looks = {}, grain = true, vignette = true, bg = '#0E0C1E', vertical = {} }) => {
  const f = useCurrentFrame();
  const seg = segAt(tl, f);
  const Shot = shots[seg.shot];
  const info = tl.shots.find((s) => s.id === seg.shot);
  const run = lookRuns(tl).find((r) => f >= r.a && f < r.b);
  const def = run ? looks[run.look] : undefined;
  const lv = run ? Math.min(clamp((f - run.a + 1) / 2), clamp((run.b - f) / 2)) : 0;
  const jitter = def?.jitter && lv > 0 ? Math.sin(f * 13.7) * def.jitter * lv : 0;
  const { flash, x, y } = fxAt(tl, f);
  const A = tl.audio;
  const r = vertical[seg.shot] ?? {};
  const len = info?.len ?? seg.b - seg.a;
  const tt = clockAt(seg, f);
  const shot = Shot ? <Shot t={tt} len={len} f={f} /> : null;
  const fw = r.fit ? r.w ?? 1920 : 1920;
  const fitH = (VW * 1080) / fw;
  const band = `${(r.cx ?? 960) - fw / 2} 0 ${fw} 1080`;
  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <AbsoluteFill style={{ transform: `translate(${x + jitter}px, ${y}px) scale(${x || y ? 1.02 : 1})`, filter: def?.grade && lv > 0 ? def.grade(lv) : undefined }}>
        {r.fit ? (
          <>
            <VShot r={{ cx: 960, cy: 540, w: 700 }} blur={28}>
              {shot}
            </VShot>
            <svg width={VW} height={fitH} viewBox={band} style={{ position: 'absolute', left: 0, top: (VH - fitH) / 2, boxShadow: '0 0 60px rgba(0,0,0,0.6)' }}>
              <KitDefs />
              <SetDefs />
              {shot}
            </svg>
          </>
        ) : (
          <VShot r={r} p={tt / Math.max(1, len)}>
            {shot}
          </VShot>
        )}
      </AbsoluteFill>
      <VGrade f={f} grain={grain} vignette={vignette} />
      {def?.Overlay && run ? (
        <svg width={VW} height={VH} viewBox={`0 0 1920 ${(1920 * VH) / VW}`} style={{ position: 'absolute', inset: 0, opacity: lv }}>
          <g transform="translate(0 260)">
            <def.Overlay f={f} lv={lv} p={clamp((f - run.a) / (run.b - run.a))} n={run.n} />
          </g>
        </svg>
      ) : null}
      {flash ? <AbsoluteFill style={{ backgroundColor: flash.color, opacity: flash.o }} /> : null}
      {A.voice ? <Audio src={staticFile(A.voice)} volume={A.voiceVol ?? 1} /> : null}
      {A.sfx ? <Audio src={staticFile(A.sfx)} volume={A.sfxVol ?? 1} /> : null}
      {A.music ? <Audio src={staticFile(A.music)} volume={A.musicVol ?? 1} /> : null}
    </AbsoluteFill>
  );
};

/** The vertical storyboard: frame i is shot i at its key frame, reframed. */
export const VerticalBoard: React.FC<{ timeline: Timeline; shots: ShotMap; vertical?: Record<string, Reframe> }> = ({ timeline: tl, shots, vertical = {} }) => {
  const f = useCurrentFrame();
  const info = tl.shots[Math.min(f, tl.shots.length - 1)];
  const Shot = shots[info.id];
  const r = vertical[info.id] ?? {};
  const shot = Shot ? <Shot t={info.key} len={info.len} f={info.first + info.key} /> : null;
  const fw = r.fit ? r.w ?? 1920 : 1920;
  const fitH = (VW * 1080) / fw;
  const band = `${(r.cx ?? 960) - fw / 2} 0 ${fw} 1080`;
  return (
    <AbsoluteFill style={{ backgroundColor: '#0E0C1E' }}>
      {r.fit ? (
        <>
          <VShot r={{ cx: 960, cy: 540, w: 700 }} blur={28}>
            {shot}
          </VShot>
          <svg width={VW} height={fitH} viewBox={band} style={{ position: 'absolute', left: 0, top: (VH - fitH) / 2, boxShadow: '0 0 60px rgba(0,0,0,0.6)' }}>
            <KitDefs />
            <SetDefs />
            {shot}
          </svg>
        </>
      ) : (
        <VShot r={r} p={info.key / Math.max(1, info.len)}>
          {shot}
        </VShot>
      )}
      <VGrade f={info.key} grain vignette />
    </AbsoluteFill>
  );
};

/** Bundle an episode for the registry: the main composition and its storyboard (and the vertical cut when it has one). */
export const defineEpisode = (id: string, p: EpisodeProps) => ({
  id,
  total: p.timeline.total,
  shotCount: p.timeline.shots.length,
  Main: () => <Episode {...p} />,
  Board: () => <Board timeline={p.timeline} shots={p.shots} grain={p.grain} vignette={p.vignette} bg={p.bg} />,
  Vertical: p.vertical ? () => <VerticalEpisode {...p} /> : null,
  VerticalBoard: p.vertical ? () => <VerticalBoard timeline={p.timeline} shots={p.shots} vertical={p.vertical} /> : null,
});
export type EpisodeDef = ReturnType<typeof defineEpisode>;
