import React from 'react';
import {
  Hero, Pose, basePose, poseAt, faceAt, kf, clamp, easeOut, easeInOut, backOut, rnd, camT, LOOKS, LEG_LEN, HEAD,
  Kitchen, KitchenIsland, KITCHEN, islandTop, Study, STUDY, Desk, stand, Rooftop, Schematic, SCH, SchLabel, CountUp, DrawOn, Arrow,
  Glow, Sparkle, TitleCard, Foreground, FONT, UI, ShotProps, Stars, Moon,
} from '../../engine';
import * as FR from '../grandir/shots';
import { GOLD, growth, feetAt, GrowFx, Figure, Cube, StreetSet, Pigeons, SUIT_AT, MOM_AT, STREET, Giant } from '../grandir/shots';

// « What if you could grow at will? » The English long cut (60 s and more), for YouTube. It plays the French episode's
// shots again where they carry no words, redraws the ones with text on them in English, and adds eight shots: the study,
// the colossus, the pigeons, Mo in Pip's palm, two more schematics, the night on the rooftop and the end card.
//
// The French shots were timed on the French voice. Here each one is re-anchored to the end of its segment, so the
// action (the growth, the landing, the snap) always falls in the pause after its word, whatever voice is laid in.

const PIP = LOOKS.pipHood;
const MO = LOOKS.mo;
const SUIT = LOOKS.suit;
const MOM = LOOKS.mom;
const fmt = (v: number) => Math.round(v).toLocaleString('en-US');

/** Replays a shot with its clock shifted so that the frame `at` of the original lands `before` frames from the end. */
const endAnchored = (Shot: React.FC<ShotProps>, at: number, before: number): React.FC<ShotProps> => ({ t, len, f }) => (
  <Shot t={t - (len - before - at)} len={len} f={f} />
);

// ---------- the French shots, replayed ----------
export const S1 = FR.S1;
export const S2 = FR.S2;
export const S3 = endAnchored(FR.S3, 14, 10);
export const S4 = endAnchored(FR.S4, 17, 7);
export const S5 = endAnchored(FR.S5, 26, 10);
export const S6 = endAnchored(FR.S6, 15, 10);
export const S7 = endAnchored(FR.S7, 22, 6);
export const S8 = FR.S8;
export const S9 = endAnchored(FR.S9, 14, 10);
export const S10 = endAnchored(FR.S10, 17, 10);
export const S11 = endAnchored(FR.S11, 17, 10);
export const S12 = FR.S12;
export const S14 = endAnchored(FR.S14, 21, 26);
export const S15 = FR.S15;
export const S18 = endAnchored(FR.S18, 50, 7);
export const S19 = FR.S19;
export const S20 = FR.S20;
export const S22 = FR.S22;
export const S23 = endAnchored(FR.S23, 51, 9);
export const S24 = endAnchored(FR.S24, 86, 6);

// ---------- the shots with words on them, in English ----------
// S13: the title, wide: Pip among the buildings at dusk, waving at the sun going down
export const S13: React.FC<ShotProps> = ({ t, len }) => {
  const s = 2.8;
  const pose = poseAt(t, [
    { f: 0, p: { x: 1330, y: feetAt(1150, s), scale: s, yaw: -0.3, look: -0.4, armL: { a: 24, b: 10 }, armR: { a: 22, b: 8 } } },
    { f: 26, p: { headTilt: -3 } },
    { f: 36, p: { armL: { a: 148, b: 14 }, headTilt: 2 }, ease: easeOut },
    { f: 44, p: { armL: { a: 140, b: 30 } } },
    { f: 52, p: { armL: { a: 150, b: 10 } } },
    { f: 60, p: { armL: { a: 140, b: 30 } } },
  ]);
  return (
    <g transform={camT(960, kf(t, [[0, 520], [len, 545]]), kf(t, [[0, 1.0], [len, 1.06]]))}>
      <Rooftop t={t} sunX={1040} sunY={kf(t, [[0, 690], [len, 705]])} low={260} between={<Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'happy']]) }} rimId="rimL" shadow={0} />} />
      <TitleCard t={t} lines={['WHAT IF YOU COULD', 'GROW AT WILL?']} accent="GROW" accentT={Math.round(len * 0.5)} size={118} y={150} />
    </g>
  );
};

// S16: schematic: ten times taller, a thousand times heavier
export const S16: React.FC<ShotProps> = ({ t, len }) => (
  <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
    <Schematic t={t} id="esch16" />
    <DrawOn d="M 170 900 L 900 900" t={t} dur={8} color={SCH.dim} width={3} />
    <Figure x={260} y={900} h={64} t={t - 2} />
    <Figure x={610} y={900} h={640} t={t - 6} color={GOLD} />
    <Arrow x0={790} y0={900} x1={790} y1={268} t={t - 16} dur={10} color={SCH.live} bend={0} />
    <SchLabel x={260} y={960} t={t - 4} text="×1" size={40} color={SCH.dim} />
    <SchLabel x={610} y={960} t={t - 14} text="HEIGHT ×10" size={46} color={GOLD} />
    <Cube x={1040} y={760} a={40} t={t - 26} />
    <SchLabel x={1060} y={850} t={t - 28} text="1" size={36} color={SCH.dim} />
    <Arrow x0={1120} y0={780} x1={1190} y1={720} t={t - 30} dur={6} />
    <Cube x={1230} y={420} a={400} t={t - 32} grid={10} color={GOLD} />
    <SchLabel x={1500} y={240} t={t - 36} text="WEIGHT" size={40} color={SCH.dim} />
    <CountUp x={1500} y={960} t={t - 36} to={1000} dur={22} size={92} format={(v) => `×${fmt(Math.max(1, v))}`} />
  </g>
);

// S17: schematic: the bone's cross-section ten times wider is only a hundred times stronger
export const S17: React.FC<ShotProps> = ({ t, len }) => {
  const r1 = 22;
  const r2 = 240;
  const cx = 1060;
  const cy = 520;
  const fill = clamp((t - 30) / 22);
  const cells: React.ReactNode[] = [];
  for (let i = 0; i < 10; i++)
    for (let k = 0; k < 10; k++) {
      const n = i * 10 + k;
      if (n < fill * 100) cells.push(<rect key={n} x={cx - r2 + k * 48 + 3} y={cy - r2 + i * 48 + 3} width={42} height={42} rx={4} fill={GOLD} opacity={0.35} />);
    }
  return (
    <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
      <Schematic t={t + 74} id="esch17" />
      <DrawOn d="M 230 330 q -36 -40 0 -64 q 30 -14 44 18 L 410 230 q 14 -32 44 -18 q 36 24 0 64 q 36 40 0 64 q -30 14 -44 -18 L 274 380 q -14 32 -44 18 q -36 -24 0 -64 Z" t={t - 2} dur={12} color={SCH.line} width={4} />
      <SchLabel x={342} y={460} t={t - 8} text="THIGH BONE" size={34} color={SCH.dim} />
      <circle cx={342} cy={600} r={r1} fill="none" stroke={SCH.line} strokeWidth={4} opacity={clamp((t - 10) / 5)} />
      <SchLabel x={342} y={680} t={t - 12} text="CROSS-SECTION ×1" size={30} color={SCH.dim} />
      <Arrow x0={420} y0={600} x1={760} y1={560} t={t - 16} dur={8} />
      <SchLabel x={590} y={540} t={t - 20} text="×10 WIDER" size={30} color={GOLD} />
      <defs>
        <clipPath id="es17sec">
          <circle cx={cx} cy={cy} r={r2} />
        </clipPath>
      </defs>
      <g clipPath="url(#es17sec)">{cells}</g>
      {t > 18 ? <circle cx={cx} cy={cy} r={r2 * easeOut(clamp((t - 18) / 10))} fill="none" stroke={GOLD} strokeWidth={6} /> : null}
      <SchLabel x={1560} y={460} t={t - 30} text="STRENGTH" size={42} color={SCH.dim} />
      <CountUp x={1560} y={580} t={t - 32} to={100} dur={18} size={96} format={(v) => `×${Math.max(1, Math.round(v))}`} />
      <SchLabel x={1560} y={660} t={t - 44} text="ONLY" size={34} color={SCH.live} />
    </g>
  );
};

/** A photo print: a giant hooded silhouette over a city at dusk, two gold eyes, a date in pen. x, y its centre. */
const Photo: React.FC<{ x: number; y: number; w: number; rot?: number }> = ({ x, y, w, rot = 0 }) => {
  const h = w * 1.18;
  const iw = w * 0.86;
  const top = -h / 2 + w * 0.07;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot})`}>
      <rect x={-w / 2 + 6} y={-h / 2 + 8} width={w} height={h} fill="#000" opacity={0.35} />
      <rect x={-w / 2} y={-h / 2} width={w} height={h} fill="#F2EEE6" />
      <defs>
        <clipPath id="ephotoClip">
          <rect x={-iw / 2} y={top} width={iw} height={iw} />
        </clipPath>
      </defs>
      <g clipPath="url(#ephotoClip)">
        <rect x={-iw / 2} y={top} width={iw} height={iw} fill="#6E3A6E" />
        <rect x={-iw / 2} y={top + iw * 0.55} width={iw} height={iw * 0.45} fill="#F2985A" />
        <circle cx={iw * 0.05} cy={top + iw * 0.45} r={iw * 0.33} fill="#1A1424" />
        <circle cx={iw * 0.05} cy={top + iw * 0.5} r={iw * 0.24} fill="#E6DCCB" />
        <circle cx={iw * -0.03} cy={top + iw * 0.47} r={iw * 0.03} fill={GOLD} />
        <circle cx={iw * 0.13} cy={top + iw * 0.47} r={iw * 0.03} fill={GOLD} />
        {Array.from({ length: 8 }).map((_, i) => (
          <rect key={i} x={-iw / 2 + i * iw * 0.13} y={top + iw * (0.72 + rnd(95, i) * 0.12)} width={iw * 0.13} height={iw} fill="#2A2038" />
        ))}
      </g>
      <text x={0} y={h / 2 - w * 0.07} textAnchor="middle" fontFamily={FONT.hand} fontSize={w * 0.1} fill="#3A3444">
        last night, 7:42
      </text>
    </g>
  );
};

// S21: medium, low: « He has a photo of you. And an offer. » The man in the suit slides a photo across the island
export const S21: React.FC<ShotProps> = ({ t, len }) => {
  const slide = easeOut(clamp((t - 8) / 14));
  const ph = islandTop(0.5, 0.7);
  const suit = poseAt(t, [
    { f: 0, p: { x: SUIT_AT.x, y: SUIT_AT.y, scale: SUIT_AT.scale, yaw: -0.35, look: -0.5, armL: { a: 8, b: -6 }, armR: { a: 40, b: 30 } } },
    { f: 8, p: { armR: { a: 50, b: 40 } } },
    { f: 22, p: { armR: { a: 36, b: 22 }, headTilt: -3, look: -0.9 }, ease: easeOut },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 1010], [len, 1000]]), kf(t, [[0, 560], [len, 570]]), kf(t, [[0, 2.0], [len, 2.16]]))}>
      <g filter="url(#blur3)">
        <Kitchen t={t + 340} id="ek21" veil={0.42} />
        <Hero look={MOM} pose={{ ...basePose, x: MOM_AT.x, y: MOM_AT.y, scale: MOM_AT.scale, yaw: -0.4, look: -0.6, armL: { a: 30, b: 70 }, armR: { a: 30, b: 70 }, expr: 'worried' }} rimId="rimL" shadow={0} />
      </g>
      <Hero look={SUIT} pose={{ ...suit, ...faceAt(t, [[0, 'neutral'], [Math.max(30, len - 30), 'smug']]) }} rimId="rimL" shadow={0} />
      <KitchenIsland stools={false} />
      <Photo x={ph.x + 60 - slide * 150} y={ph.y - 4} w={92} rot={-8 + slide * 14} />
      <Glow x={ph.x - 60} y={ph.y - 40} r={220} o={0.25} />
    </g>
  );
};

// ---------- the new shots ----------
const ST = stand(STUDY, 0.8, 0.5);
const ST_FLOOR = ST.y + LEG_LEN * ST.scale;
const ST_CEIL = STUDY.P(0.8, 0, 0.5).y;

// S25: medium wide, the study: « One word, and you get bigger. » Pip says it; the lamp shakes, the books jump
const S25raw: React.FC<ShotProps> = ({ t, len }) => {
  const big = (ST_FLOOR - ST_CEIL) / 396 * 0.97;
  const g = growth(t, 18, ST.scale, big, 6);
  const pose = poseAt(t, [
    { f: 0, p: { x: ST.x, yaw: -0.35, look: -0.6, armL: { a: 14, b: -8 }, armR: { a: 14, b: -8 } } },
    { f: 8, p: { headTilt: -4 } },
    { f: 17, p: { armL: { a: 24, b: 40 }, armR: { a: 24, b: 40 } } },
    { f: 22, p: { armL: { a: 80, b: 10 }, armR: { a: 80, b: 10 }, headTilt: -6 }, ease: easeOut },
    { f: 26, p: { headTilt: 10, tilt: -4 } },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 1150], [len, 1130]]), kf(t, [[0, 590], [len, 560]]), kf(t, [[0, 1.45], [len, 1.3]]))}>
      <Study t={t + 500} id="st25" />
      <Desk x0={560} x1={1100} y={700} />
      <GrowFx x={ST.x} y={ST_FLOOR} t={t - 18} s={1.1} />
      <Hero look={PIP} pose={{ ...pose, y: feetAt(ST_FLOOR, g.scale), scale: g.scale, squash: g.squash, glint: g.glint, glintColor: GOLD, ...faceAt(t, [[0, 'smug'], [20, 'happy']]) }} rimId="rimL" shadow={0.8} />
      <Foreground blur={10}>
        <path d="M 1560 1000 Q 1460 780 1520 600 Q 1560 780 1660 980 Z" fill="#0E1610" />
      </Foreground>
    </g>
  );
};
export const S25 = endAnchored(S25raw, 18, 12);

// S26: wide: « As big as you like. Sounds amazing. » The colossus over the town, arms wide, clouds round his head
export const S26: React.FC<ShotProps> = ({ t, len }) => {
  const s = 4.2;
  const pose = poseAt(t, [
    { f: 0, p: { x: 960, y: feetAt(1700, s), scale: s, yaw: 0.05, look: 0.2, armL: { a: 60, b: 20 }, armR: { a: 60, b: 20 } } },
    { f: 14, p: { armL: { a: 120, b: 10 }, armR: { a: 120, b: 10 } }, ease: easeOut },
    { f: 40, p: { armL: { a: 128, b: 6 }, armR: { a: 128, b: 6 }, headTilt: 3 } },
  ]);
  const drift = (t * 1.4) % 2400;
  return (
    <g transform={camT(960, kf(t, [[0, 560], [len, 520]]), kf(t, [[0, 1.12], [len, 1.0]]))}>
      <StreetSet t={t + 40} id="est26" sunX={1500} sunY={640}>
        <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'happy']]) }} rimId="rimR" shadow={0} />
      </StreetSet>
      <g filter="url(#blur10)" opacity={0.85}>
        {[[200, 80, 260, 40], [1300, 640, 340, 46], [700, 700, 240, 30]].map(([x, y, rx, ry], i) => (
          <ellipse key={i} cx={((x + drift * (i % 2 ? 1 : 0.6)) % 2600) - 300} cy={y} rx={rx} ry={ry} fill="#C88AA8" opacity={0.75} />
        ))}
      </g>
      <Pigeons x={960} y={kf(t, [[0, 330], [len, 300]])} t={t} rx={520} ry={110} n={7} />
    </g>
  );
};

/** A pigeon perched (or flapping in when `flap` > 0), side view, facing right, x y the feet. */
const Pigeon: React.FC<{ x: number; y: number; s?: number; t: number; flap?: number; flip?: boolean; seed?: number }> = ({ x, y, s = 1, t, flap = 0, flip = false, seed = 0 }) => {
  const bob = Math.sin(t / 3 + seed) * 2 * (1 - flap);
  const peck = Math.max(0, Math.sin(t / 7 + seed * 2)) ** 8 * 10 * (1 - flap);
  const wing = flap > 0 ? Math.sin(t * 1.3) * 40 * flap : 0;
  return (
    <g transform={`translate(${x} ${y}) scale(${(flip ? -1 : 1) * s} ${s})`}>
      <ellipse cx={0} cy={2} rx={22} ry={4} fill="#000" opacity={0.25} />
      <path d="M -4 0 L -6 -10 M 6 0 L 4 -10" stroke="#C2553E" strokeWidth={3} />
      <ellipse cx={-6} cy={-24 + bob} rx={30} ry={18} fill="#7E8296" />
      <path d={`M -34 -26 L -54 -18 L -36 -16 Z`} fill="#4E5264" />
      <path d={`M -14 ${-30 + bob} Q -2 ${-52 + bob - wing} 18 ${-34 + bob}`} fill="#6A6E82" stroke="#3E4252" strokeWidth={2} />
      <g transform={`translate(${18 + peck * 0.6} ${-40 + bob + peck})`}>
        <circle cx={0} cy={0} r={12} fill="#8A8EA4" />
        <path d="M 4 6 Q 10 14 2 18" stroke="#5FA88A" strokeWidth={5} fill="none" opacity={0.8} />
        <circle cx={4} cy={-3} r={2.6} fill="#1A1622" />
        <path d="M 11 -1 L 20 2 L 11 4 Z" fill="#E9C46A" />
      </g>
    </g>
  );
};

// S27: close-up: « Pigeons think you're a building. » Pigeons perched on his hood; one more lands
export const S27: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 5.6;
  const head = { x: 900, y: 700 };
  const top = head.y - (HEAD.r + 18) * sc;
  const land = clamp((t - 6) / 14);
  const pose: Pose = {
    ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: 0.15, look: kf(t, [[0, 0.6], [16, -0.2], [30, 0.5]]), headTilt: kf(t, [[0, 0], [len, -3]]),
    armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'neutral'], [18, 'oops']]),
  };
  return (
    <g transform={camT(960, 540, kf(t, [[0, 1.0], [len, 1.05]]))}>
      <g filter="url(#blur16)">
        <g transform="translate(-560 -640) scale(2)">
          <Rooftop t={t + 260} sunX={1300} sunY={600} low={320} strings={false} />
        </g>
      </g>
      <rect x={-200} y={-200} width={2320} height={1480} fill="#07040C" opacity={0.2} />
      <Hero look={PIP} pose={pose} rimId="rimR" shadow={0} />
      <Pigeon x={head.x - 200} y={top + 60} s={2.2} t={t} seed={1} />
      <Pigeon x={head.x + 40} y={top + 6} s={2.3} t={t} seed={2} flip />
      <Pigeon x={kf(t, [[0, 1800], [20, head.x + 250]], easeOut)} y={kf(t, [[0, 120], [20, top + 70]], easeOut)} s={2.2} t={t} flap={1 - land} seed={3} flip={false} />
    </g>
  );
};

// S28: wide: « Your best friend gets the best seat in town. » Mo sits in Pip's open palm, high over the city
export const S28: React.FC<ShotProps> = ({ t, len }) => {
  const lift = kf(t, [[0, 40], [len, -20]]);
  const palm = { x: 980, y: 700 + lift };
  const mo = poseAt(t, [
    { f: 0, p: { x: palm.x + 20, y: palm.y - 30, scale: 0.95, yaw: 0.8, facing: 1, look: 1, legL: { a: 84, b: -84 }, legR: { a: 76, b: -70 }, armL: { a: 30, b: 20 }, armR: { a: 40, b: 30 } } },
    { f: 10, p: { armR: { a: 150, b: 20 } }, ease: easeOut },
    { f: 18, p: { armR: { a: 140, b: 40 } } },
    { f: 26, p: { armR: { a: 152, b: 18 } } },
    { f: 34, p: { armR: { a: 140, b: 40 } } },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 980], [len, 990]]), kf(t, [[0, 560], [len, 540]]), kf(t, [[0, 1.08], [len, 1.14]]))}>
      <Rooftop t={t + 300} sunX={1380} sunY={620} low={420} strings={false} />
      {/* Pip's sleeve and mitten, huge, coming in from the lower left */}
      <g filter="url(#rimR)">
        <path d={`M -200 1300 Q 300 1000 ${palm.x - 260} ${palm.y + 120}`} stroke={PIP.line} strokeWidth={300} fill="none" strokeLinecap="round" />
        <path d={`M -200 1300 Q 300 1000 ${palm.x - 260} ${palm.y + 120}`} stroke={PIP.limb} strokeWidth={270} fill="none" strokeLinecap="round" />
        <ellipse cx={palm.x} cy={palm.y + 40} rx={300} ry={110} fill={PIP.hand} stroke={PIP.line} strokeWidth={12} />
        <ellipse cx={palm.x - 250} cy={palm.y - 40} rx={60} ry={110} fill={PIP.hand} stroke={PIP.line} strokeWidth={12} transform={`rotate(-25 ${palm.x - 250} ${palm.y - 40})`} />
        <path d={`M ${palm.x - 120} ${palm.y + 70} Q ${palm.x} ${palm.y + 100} ${palm.x + 140} ${palm.y + 70}`} stroke={PIP.line} strokeWidth={6} fill="none" opacity={0.35} />
      </g>
      <Hero look={MO} pose={{ ...mo, ...faceAt(t, [[0, 'happy']]) }} rimId="rimR" shadow={0} />
      <Pigeons x={1300} y={300} t={t + 30} rx={300} ry={70} n={4} />
      {t > 12 ? <Sparkle x={palm.x + 160} y={palm.y - 260} t={t - 12} s={1} /> : null}
    </g>
  );
};

// S29: schematic: « So every square inch of bone carries ten times the load. »
export const S29: React.FC<ShotProps> = ({ t, len }) => {
  const stack = (x: number, n: number, t0: number, color: string) =>
    Array.from({ length: n }).map((_, i) => {
      const tt = t - t0 - i * 2;
      if (tt < 0) return null;
      const drop = (1 - easeOut(clamp(tt / 5))) * 60;
      return <rect key={i} x={x - 70} y={760 - (i + 1) * 46 - drop} width={140} height={40} rx={6} fill={color} opacity={0.85} stroke={SCH.line} strokeWidth={3} />;
    });
  return (
    <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
      <Schematic t={t + 150} id="esch29" />
      {/* one square inch of bone, before and after */}
      <DrawOn d="M 380 760 L 560 760 L 560 840 L 380 840 Z" t={t} dur={8} />
      <SchLabel x={470} y={900} t={t - 4} text="1 SQUARE INCH" size={30} color={SCH.dim} />
      {stack(470, 1, 6, SCH.dim)}
      <SchLabel x={470} y={640} t={t - 10} text="×1" size={44} color={SCH.line} />
      <DrawOn d="M 1180 760 L 1360 760 L 1360 840 L 1180 840 Z" t={t - 12} dur={8} color={GOLD} />
      <SchLabel x={1270} y={900} t={t - 16} text="SAME SQUARE INCH, AT ×10" size={30} color={GOLD} />
      {stack(1270, 10, 18, SCH.live)}
      <SchLabel x={1270} y={240} t={t - 42} text="×10 THE LOAD" size={54} color={SCH.live} />
      <SchLabel x={830} y={420} t={t - 30} text="WEIGHT ×1,000" size={40} />
      <DrawOn d="M 690 450 L 970 450" t={t - 32} dur={6} color={SCH.dim} width={4} />
      <SchLabel x={830} y={500} t={t - 34} text="BONE ×100" size={40} />
    </g>
  );
};

// S30: schematic: « And a human thigh bone breaks at about ten times your body weight. » The load climbs to the line
export const S30: React.FC<ShotProps> = ({ t, len }) => {
  const p = easeInOut(clamp((t - 10) / Math.max(20, len - 22)));
  const broke = p > 0.98;
  const h = 560;
  const y0 = 860;
  return (
    <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
      <Schematic t={t + 220} id="esch30" />
      <g transform="translate(560 540) scale(2.4) translate(-302 -305)">
        <DrawOn d="M 150 330 q -36 -40 0 -64 q 30 -14 44 18 L 410 230 q 14 -32 44 -18 q 36 24 0 64 q 36 40 0 64 q -30 14 -44 -18 L 194 380 q -14 32 -44 18 q -36 -24 0 -64 Z" t={t} dur={12} color={broke ? UI.bad : SCH.line} width={3} />
        {broke ? <DrawOn d="M 290 262 L 302 290 L 290 304 L 310 344" t={(t - (10 + Math.max(20, len - 22))) * 2} dur={4} color={UI.bad} width={5} /> : null}
      </g>
      <SchLabel x={560} y={860} t={t - 4} text="HUMAN THIGH BONE" size={34} color={SCH.dim} />
      {/* the gauge: body weights of load, up to the breaking line at ×10 */}
      <rect x={1380} y={y0 - h} width={90} height={h} rx={14} fill="none" stroke={SCH.line} strokeWidth={4} />
      <rect x={1390} y={y0 - h * p * 0.98} width={70} height={h * p * 0.98} rx={8} fill={p > 0.85 ? UI.bad : SCH.live} opacity={0.85} />
      <path d={`M 1340 ${y0 - h * 0.98} L 1510 ${y0 - h * 0.98}`} stroke={UI.bad} strokeWidth={6} strokeDasharray="14 8" />
      <SchLabel x={1700} y={y0 - h * 0.98 + 12} t={t - 6} text="BREAKS" size={40} color={UI.bad} />
      <SchLabel x={1700} y={y0 - h * 0.98 + 56} t={t - 8} text="~×10 BODY WEIGHT" size={28} color={UI.bad} />
      <CountUp x={1425} y={y0 + 70} t={t - 10} to={10} dur={Math.max(20, len - 22)} size={60} format={(v) => `×${Math.max(1, Math.round(v))}`} />
      <SchLabel x={1425} y={y0 + 120} t={t - 10} text="LOAD" size={28} color={SCH.dim} />
    </g>
  );
};

// S31: wide: « You sit down on a rooftop and wait to shrink back. » Night falls, he shrinks slowly on the roof
export const S31: React.FC<ShotProps> = ({ t, len }) => {
  const k = easeInOut(clamp(t / len));
  const s = 2.3 - 1.25 * k;
  const seat = { x: 1180, y: 700 };
  const pose = poseAt(t, [
    { f: 0, p: { x: seat.x, y: seat.y, scale: s, yaw: -0.85, facing: -1, look: -0.4, tilt: -6, headTilt: -8, legL: { a: 82, b: -78 }, legR: { a: 76, b: -60 }, armL: { a: 40, b: -30 }, armR: { a: 30, b: -20 } } },
    { f: len, p: { headTilt: 6, look: 0.2 } },
  ]);
  return (
    <g transform={camT(1050, kf(t, [[0, 560], [len, 600]]), kf(t, [[0, 1.0], [len, 1.12]]))}>
      <StreetSet
        t={t + 120}
        id="est31"
        red={0.6 * (1 - k)}
        sunX={700}
        sunY={640 + 300 * k}
        front={
          <g>
            <rect x={-400} y={-400} width={2720} height={1900} fill="#070B22" opacity={0.6 * k} />
            <Stars seed={7} x0={-200} y0={-200} w={2320} h={700} t={t} n={60} o={0.9 * k} />
            <g opacity={k}>
              <Moon x={420} y={240} r={60} bloom={k} />
            </g>
            <rect x={seat.x - 140} y={seat.y} width={520} height={600} fill="#120A16" />
            <rect x={seat.x - 140} y={seat.y} width={520} height={14} fill="#241826" />
            <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'worried'], [Math.round(len * 0.6), 'tired']]) }} rimId={k > 0.5 ? 'rimBlue' : 'rimRed'} shadow={0} />
            {Array.from({ length: 8 }).map((_, i) => {
              const tt = (t * 0.6 + i * 9) % 30;
              return <circle key={i} cx={seat.x - 40 + rnd(71, i) * 120} cy={seat.y - 80 - tt * 6} r={3} fill={GOLD} opacity={0.6 * (1 - tt / 30) * clamp(t / 10)} />;
            })}
          </g>
        }
      />
    </g>
  );
};

// S32: the end card: PART 1, WHAT WOULD YOU DO? over the cracked ceiling, in the dark
export const S32: React.FC<ShotProps> = ({ t, len }) => (
  <g>
    <g opacity={0.3}>
      <FR.S22 t={t + 40} len={len} f={0} />
    </g>
    <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.45} />
    <TitleCard t={t} lines={['PART 1', 'WHAT WOULD YOU DO?']} accent="YOU" accentT={22} size={110} y={460} />
  </g>
);

// keep the shared names in use (Giant and STREET belong to the replayed rooftop shots)
export const _shared = [Giant, STREET, KITCHEN, backOut];
