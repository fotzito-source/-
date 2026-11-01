import React from 'react';
import {
  Hero, Pose, basePose, poseAt, faceAt, kf, clamp, easeOut, easeInOut, backOut, rnd, settle, camT, LOOKS, LEG_LEN, HEAD, joints, toWorld,
  Kitchen, KitchenIsland, KITCHEN, islandTop, stand, Stairwell, Banister, SW, Rooftop, Study, Schematic, SCH, SchLabel, CountUp, DrawOn, Arrow,
  Cookie, Foreground, Glow, Sparkle, TitleCard, FocusRings, FONT, UI, ShotProps, DuskSky, Sun, Skyline, Haze,
} from '../../engine';

// « Et si tu pouvais grandir à volonté ? » Twenty-four shots on the kitchen, the stairwell, the rooftop (with a giant in
// the street behind it), the schematic and a blurred bedroom upstairs. The power: one word, and Pip grows. Its look is a
// gold pulse from the feet, eyes that light up gold, a height ruler in the overlay (index.tsx). Every shot is a pure
// function of its own clock t.

const PIP = LOOKS.pipHood;
const MO = LOOKS.mo;
const MOM = LOOKS.mom;
const SUIT = LOOKS.suit;
const SIS = LOOKS.sis;
export const GOLD = '#FFC94A';

// ---------- the power, shared by every growth ----------
/** A growth from `from` to `to`: a crouch before, the push up with an overshoot, a settle. Feet stay where they are. */
const growth = (t: number, t0: number, from: number, to: number, dur = 8) => {
  const u = clamp((t - t0) / dur);
  const scale = from + (to - from) * backOut(u);
  const crouch = clamp((t - (t0 - 5)) / 5) * (1 - clamp((t - t0) / 2));
  const squash = t < t0 ? 0.09 * crouch : t < t0 + dur ? -0.07 * Math.sin(u * Math.PI) : settle(t - t0 - dur, 0.05, 1.7, 4);
  const glint = clamp((t - t0 + 2) / 3) * (1 - clamp((t - t0 - dur - 6) / 8));
  return { scale, squash, glint };
};
/** The hip point for someone whose feet are on `floor` at this scale. */
const feetAt = (floor: number, scale: number) => floor - LEG_LEN * scale;

/** The power's mark on the world: a gold ring opening on the floor round the feet, sparks rising, a glow. */
const GrowFx: React.FC<{ x: number; y: number; t: number; s?: number; h?: number }> = ({ x, y, t, s = 1, h = 420 }) => {
  if (t < 0 || t > 22) return null;
  const k = easeOut(clamp(t / 16));
  return (
    <g style={{ mixBlendMode: 'screen' }}>
      <ellipse cx={x} cy={y} rx={(60 + 260 * k) * s} ry={(14 + 58 * k) * s} fill="none" stroke={GOLD} strokeWidth={7 * s} opacity={1 - clamp(t / 18)} />
      <ellipse cx={x} cy={y} rx={(30 + 160 * k) * s} ry={(8 + 34 * k) * s} fill="none" stroke="#FFF3C4" strokeWidth={3.5 * s} opacity={0.85 * (1 - clamp(t / 14))} />
      {Array.from({ length: 16 }).map((_, i) => {
        const px = x + (rnd(7, i) - 0.5) * 240 * s;
        const py = y - (rnd(8, i) * 0.35 + t / 22) * h * s;
        return <circle key={i} cx={px} cy={py} r={(2.5 + rnd(9, i) * 4) * s} fill="#FFE7A0" opacity={(1 - t / 22) * (0.5 + rnd(10, i) * 0.5)} />;
      })}
      <Glow x={x} y={y - 80 * s} r={280 * s} o={0.55 * (1 - clamp(t / 18))} />
    </g>
  );
};

/** A glass jar of cookies with a wooden lid; x, y is the middle of its base. */
const CookieJar: React.FC<{ x: number; y: number; s?: number; lid?: number; n?: number }> = ({ x, y, s = 1, lid = 0, n = 6 }) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    <ellipse cx={2} cy={1} rx={44} ry={8} fill="#000" opacity={0.4} />
    {Array.from({ length: n }).map((_, i) => (
      <Cookie key={i} x={-14 + (i % 3) * 14 + (i > 2 ? 7 : 0)} y={-6 - Math.floor(i / 3) * 16 - (i % 2) * 3} s={0.42} rot={(i * 23) % 30 - 15} seed={40 + i} />
    ))}
    <path d="M -36 -4 Q -40 -62 -31 -74 L 31 -74 Q 40 -62 36 -4 Q 0 6 -36 -4 Z" fill="#BFD8E8" opacity={0.26} stroke="#E8F2F8" strokeWidth={2.6} />
    <path d="M -26 -14 Q -29 -46 -23 -62" stroke="#FFFFFF" strokeWidth={5} opacity={0.45} fill="none" strokeLinecap="round" />
    <path d="M 30 -10 Q 33 -40 28 -60" stroke="#FFB46A" strokeWidth={3} opacity={0.55} fill="none" strokeLinecap="round" />
    {lid >= 0 ? (
      <g transform={`translate(${lid * 26} ${-lid * 30}) rotate(${lid * 24})`}>
        <rect x={-30} y={-88} width={60} height={15} rx={5} fill="#A86E44" stroke="#4A2C1C" strokeWidth={2.5} />
        <rect x={-8} y={-98} width={16} height={11} rx={4} fill="#8A5634" stroke="#4A2C1C" strokeWidth={2.5} />
      </g>
    ) : null}
  </g>
);

// ---------- the kitchen: Pip in front of the fridge; the jar on top of it ----------
const KF = stand(KITCHEN, 0.86, 0.3); // Pip at the fridge: hips and scale at u 0.86, w 0.3
const K_FLOOR = KF.y + LEG_LEN * KF.scale;
const JAR = KITCHEN.P(0.885, 0.16, 0.11); // on top of the fridge
const K_CEIL = KITCHEN.P(0.86, 0, 0.3).y; // the ceiling line at Pip's depth
const K_BIG = (K_FLOOR - K_CEIL) / 396; // the scale at which his hood touches the ceiling

const reachPose = (t: number): Pose =>
  poseAt(t, [
    { f: 0, p: { x: KF.x, y: KF.y, scale: KF.scale, yaw: -0.25, look: -0.3, headTilt: -6, armL: { a: 120, b: 30 }, armR: { a: 14, b: -8 } } },
    { f: 8, p: { armL: { a: 152, b: 4 }, squash: -0.05, headTilt: -10 }, ease: easeOut },
    { f: 16, p: { armL: { a: 146, b: 8 }, squash: -0.03 } },
    { f: 24, p: { armL: { a: 155, b: 2 }, squash: -0.06 } },
    { f: 34, p: { armL: { a: 148, b: 6 }, squash: -0.04 } },
  ]);

// S1: medium wide: Pip on tiptoe in front of the fridge, the jar out of reach on top
export const S1: React.FC<ShotProps> = ({ t, len }) => {
  const pose = reachPose(t);
  return (
    <g transform={camT(kf(t, [[0, 1290], [len, 1300]]), 575, kf(t, [[0, 1.62], [len, 1.7]]))}>
      <Kitchen t={t + 30} id="k1" />
      <CookieJar x={JAR.x} y={JAR.y} s={1.05} />
      <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'worried'], [22, 'oops']]) }} rimId="rimL" shadow={0.8} />
      <KitchenIsland />
      <Foreground blur={10}>
        <path d="M 560 1000 Q 600 760 700 700 Q 690 840 760 1000 Z" fill="#0E1610" />
        <path d="M 640 1000 Q 700 820 820 790 Q 770 880 800 1000 Z" fill="#0C130E" />
      </Foreground>
    </g>
  );
};

// S2: insert: the jar on top of the fridge, Pip's face and mitten below, stretching, short of it
export const S2: React.FC<ShotProps> = ({ t, len }) => {
  const pose = reachPose(t + 30);
  return (
    <g transform={camT(1352, kf(t, [[0, 452], [len, 440]]), kf(t, [[0, 2.5], [len, 2.62]]))}>
      <Kitchen t={t + 70} id="k2" veil={0.42} />
      <Glow x={JAR.x} y={JAR.y - 40} r={160} o={0.35} />
      <CookieJar x={JAR.x} y={JAR.y} s={1.05} />
      <Hero look={PIP} pose={{ ...pose, ...faceAt(t + 30, [[0, 'oops']]) }} rimId="rimL" shadow={0} />
      {t > 10 ? <Sparkle x={JAR.x + 30} y={JAR.y - 70} t={t - 10} s={0.5} /> : null}
    </g>
  );
};

// S3: medium wide: « Grandis. » He crouches, shoots up, his hood bumps the ceiling, he settles hunched
export const S3: React.FC<ShotProps> = ({ t, len }) => {
  const g = growth(t, 14, KF.scale, K_BIG * 0.985, 6);
  const pose = poseAt(t, [
    { f: 0, p: { x: KF.x, yaw: -0.2, look: 0, headTilt: -4, armL: { a: 40, b: 30 }, armR: { a: 40, b: 30 } } },
    { f: 13, p: { armL: { a: 24, b: 40 }, armR: { a: 24, b: 40 }, headTilt: 0 } },
    { f: 18, p: { armL: { a: 70, b: 10 }, armR: { a: 70, b: 10 }, headTilt: -6 }, ease: easeOut },
    { f: 21, p: { headTilt: 10, tilt: 4 } },
    { f: 24, p: { armL: { a: 30, b: 16 }, armR: { a: 30, b: 16 }, headTilt: 12, tilt: 5 } },
  ]);
  const bump = clamp((t - 19) / 2) * (1 - clamp((t - 23) / 6));
  return (
    <g transform={camT(kf(t, [[0, 1310], [len, 1300]]), kf(t, [[0, 600], [len, 545]]), kf(t, [[0, 1.42], [len, 1.3]]))}>
      <Kitchen t={t + 60} id="k3" veil={0.4} />
      <CookieJar x={JAR.x} y={JAR.y} s={1.05} />
      <GrowFx x={KF.x} y={K_FLOOR} t={t - 14} s={1.1} />
      <Hero look={PIP} pose={{ ...pose, y: feetAt(K_FLOOR, g.scale), scale: g.scale, squash: g.squash, glint: g.glint, glintColor: GOLD, ...faceAt(t, [[0, 'neutral'], [19, 'oops']]) }} rimId="rimL" shadow={0.8} />
      {/* the bump: dust from the ceiling where the hood hit it */}
      {bump > 0
        ? Array.from({ length: 9 }).map((_, i) => (
            <circle key={i} cx={KF.x - 60 + rnd(3, i) * 120} cy={K_CEIL + 10 + (t - 19) * (3 + rnd(4, i) * 4)} r={3 + rnd(5, i) * 4} fill="#D9CDBA" opacity={0.8 * bump} />
          ))
        : null}
      <KitchenIsland />
    </g>
  );
};

// S4: close-up: giant Pip hunched under the ceiling, a cookie in his mitten, the jar under his arm
export const S4: React.FC<ShotProps> = ({ t, len }) => {
  const sc = K_BIG * 0.97;
  const pose = poseAt(t, [
    { f: 0, p: { x: KF.x, y: feetAt(K_FLOOR, sc), scale: sc, yaw: 0.25, look: 0.5, headTilt: 12, tilt: 5, armL: { a: 30, b: 70 }, armR: { a: 70, b: 95 } } },
    { f: 6, p: { armR: { a: 80, b: 100 } }, ease: easeOut },
    { f: 14, p: { headTilt: 14, armR: { a: 76, b: 98 } } },
  ]);
  const j = joints(pose);
  const hand = toWorld(pose, j.armR.end);
  const jarAt = toWorld(pose, j.armL.end);
  const crumbs = t > 17;
  return (
    <g transform={camT(kf(t, [[0, 1400], [len, 1410]]), kf(t, [[0, 430], [len, 420]]), kf(t, [[0, 2.3], [len, 2.42]]))}>
      <Kitchen t={t + 90} id="k4" veil={0.36} />
      <path d={`M 900 ${K_CEIL} L 1700 ${K_CEIL}`} stroke="#120E16" strokeWidth={4} opacity={0.6} />
      {/* the hairline cracks his hood left in the ceiling */}
      <path d={`M ${KF.x - 30} ${K_CEIL + 2} l 14 -10 l 10 6 l 16 -12 M ${KF.x + 10} ${K_CEIL + 2} l -6 -14`} stroke="#120E16" strokeWidth={2.5} fill="none" opacity={0.7} />
      <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'happy'], [8, 'smug']]) }} rimId="rimL" shadow={0} />
      <CookieJar x={jarAt.x + 6} y={jarAt.y + 46} s={1.0} lid={-1} n={3} />
      <Cookie x={hand.x + 4} y={hand.y + 26} s={1.1} rot={-18} bite={t >= 17 ? 1 : 0} seed={70} />
      {crumbs
        ? Array.from({ length: 6 }).map((_, i) => (
            <circle key={i} cx={hand.x - 10 + rnd(11, i) * 30} cy={hand.y + 30 + ((t - 17) * (2 + rnd(12, i) * 3)) % 140} r={2 + rnd(13, i) * 2} fill="#C98E58" />
          ))
        : null}
    </g>
  );
};

// ---------- the stairwell: late for school ----------
const LAND_X = 250; // Pip on the upper landing
const SW_BOTTOM = SW.top + SW.h * SW.n; // the lower floor's y (910)
const SW_CEIL = -150; // the stairwell's ceiling, drawn by these shots (the set has none)
const SW_BIG = 1.45;

/** A school wall clock showing a time in minutes past midnight. */
const SchoolClock: React.FC<{ x: number; y: number; r: number; min: number }> = ({ x, y, r, min }) => {
  const h = ((min / 60) % 12) * 30;
  const m = (min % 60) * 6;
  return (
    <g>
      <circle cx={x + 6} cy={y + 8} r={r} fill="#000" opacity={0.35} />
      <circle cx={x} cy={y} r={r} fill="#EFE2CC" stroke="#1E1824" strokeWidth={r * 0.14} />
      {Array.from({ length: 12 }).map((_, i) => (
        <path key={i} d={`M ${x} ${y - r * 0.82} L ${x} ${y - r * (i % 3 ? 0.74 : 0.66)}`} stroke="#1E1824" strokeWidth={r * (i % 3 ? 0.04 : 0.07)} transform={`rotate(${i * 30} ${x} ${y})`} />
      ))}
      <path d={`M ${x} ${y} L ${x} ${y - r * 0.48}`} stroke="#1E1824" strokeWidth={r * 0.1} strokeLinecap="round" transform={`rotate(${h} ${x} ${y})`} />
      <path d={`M ${x} ${y} L ${x} ${y - r * 0.72}`} stroke="#1E1824" strokeWidth={r * 0.06} strokeLinecap="round" transform={`rotate(${m} ${x} ${y})`} />
      <circle cx={x} cy={y} r={r * 0.06} fill="#C2553E" />
      <path d={`M ${x - r * 0.7} ${y - r * 0.7} A ${r} ${r} 0 0 1 ${x + r * 0.2} ${y - r}`} stroke={UI.text} strokeWidth={r * 0.05} fill="none" opacity={0.5} />
    </g>
  );
};

/** The stairwell's ceiling and cornice, so a giant has something to stoop under. */
const SwCeiling: React.FC = () => (
  <g>
    <rect x={-400} y={-600} width={2800} height={600 + SW_CEIL} fill="#1A1420" />
    <rect x={-400} y={SW_CEIL - 18} width={2800} height={18} fill="#2B2432" />
    <path d={`M -400 ${SW_CEIL} L 2400 ${SW_CEIL}`} stroke="#4E4250" strokeWidth={6} />
  </g>
);

// S5: medium: Pip on the landing; the clock hits eight
export const S5: React.FC<ShotProps> = ({ t, len }) => {
  const pose = poseAt(t, [
    { f: 0, p: { x: LAND_X, y: feetAt(SW.top, 0.9), scale: 0.9, yaw: 0.45, look: 0.9, armL: { a: 14, b: -8 }, armR: { a: 24, b: 10 }, headTilt: -4 } },
    { f: 27, p: {} },
    { f: 31, p: { armR: { a: 130, b: 40 }, armL: { a: 40, b: 30 }, squash: -0.04, headTilt: -8 }, ease: easeOut },
    { f: 35, p: { armR: { a: 122, b: 48 }, squash: 0 } },
  ]);
  const min = 7 * 60 + 59 + (t >= 26 ? 1 : 0);
  const jolt = t >= 26 ? settle(t - 26, 5, 2.2, 3) : 0;
  return (
    <g transform={camT(kf(t, [[0, 360], [len, 350]]), 250, kf(t, [[0, 1.55], [len, 1.66]]))}>
      <Stairwell t={t + 100} id="sw5" />
      <g transform={`rotate(${jolt} 560 150)`}>
        <SchoolClock x={560} y={150} r={58} min={min} />
      </g>
      {t >= 26 && t < 38 ? <FocusRings x={560} y={150} t={(t - 26) * 1.6} r0={60} color="#FFE7B3" /> : null}
      <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'neutral'], [28, 'shock']]) }} rimId="rimR" shadow={0.5} />
      <Banister />
    </g>
  );
};

// S6: wide: « Grandis. » He grows on the landing, stooped under the ceiling; the lantern sways
export const S6: React.FC<ShotProps> = ({ t, len }) => {
  const g = growth(t, 15, 0.9, SW_BIG, 6);
  const pose = poseAt(t, [
    { f: 0, p: { x: LAND_X, yaw: 0.5, look: 0.8, armL: { a: 30, b: 20 }, armR: { a: 40, b: 30 } } },
    { f: 12, p: { armL: { a: 20, b: 40 }, armR: { a: 20, b: 40 } } },
    { f: 18, p: { armL: { a: 60, b: 10 }, armR: { a: 70, b: 10 }, tilt: 8, headTilt: 10 }, ease: easeOut },
    { f: 24, p: { armL: { a: 24, b: 14 }, armR: { a: 28, b: 14 }, tilt: 10, headTilt: 14 } },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 640], [len, 650]]), kf(t, [[0, 330], [len, 320]]), kf(t, [[0, 0.92], [len, 0.88]]))}>
      <Stairwell t={t + 136} id="sw6" />
      <SwCeiling />
      <GrowFx x={LAND_X} y={SW.top} t={t - 15} s={0.9} />
      <Hero look={PIP} pose={{ ...pose, y: feetAt(SW.top, g.scale), scale: g.scale, squash: g.squash, glint: g.glint, glintColor: GOLD, ...faceAt(t, [[0, 'shock'], [19, 'smug']]) }} rimId="rimR" shadow={0.5} />
    </g>
  );
};

// S7: wide, low: « Une enjambée. » One stride from the landing to the bottom: he lands, the house jumps
export const S7: React.FC<ShotProps> = ({ t, len }) => {
  const land = 22;
  const air = clamp(t / land);
  const x = kf(t, [[0, 880], [land, 1590]], easeOut);
  const lift = Math.sin(air * Math.PI) * 120;
  const s = SW_BIG;
  const pose = poseAt(t, [
    { f: 0, p: { x: 0, y: 0, scale: s, yaw: 0.85, facing: 1, look: 0.6, tilt: 14, legL: { a: 62, b: -20 }, legR: { a: -46, b: -30 }, armL: { a: 70, b: 20 }, armR: { a: 110, b: 20 } } },
    { f: land, p: { tilt: 6, legL: { a: 30, b: -40 }, legR: { a: -20, b: -50 }, armL: { a: 80, b: 30 }, armR: { a: 80, b: 30 } } },
    { f: land + 3, p: { tilt: 2, legL: { a: 12, b: -16 }, legR: { a: -8, b: -18 }, armL: { a: 50, b: 30 }, armR: { a: 60, b: 30 } }, ease: easeOut },
    { f: land + 12, p: { tilt: 0, yaw: 0.35, legL: { a: 6, b: 0 }, legR: { a: -6, b: 0 }, armL: { a: 20, b: 10 }, armR: { a: 24, b: 12 } } },
  ]);
  const sq = t < land ? -0.05 : 0.2 * Math.exp(-(t - land) / 3) + settle(t - land - 3, 0.03, 1.8, 3);
  const dust = t - land;
  return (
    <g transform={camT(kf(t, [[0, 1500], [len, 1560]]), kf(t, [[0, 600], [len, 640]]), kf(t, [[0, 1.42], [len, 1.5]]))}>
      <Stairwell t={t + 160} id="sw7" />
      <SwCeiling />
      <Hero look={PIP} pose={{ ...pose, x, y: feetAt(SW_BOTTOM, s) - lift, squash: sq, ...faceAt(t, [[0, 'happy'], [land + 6, 'smug']]) }} rimId="rimR" shadow={t >= land ? 0.9 : 0.3} />
      {dust > 0 && dust < 20
        ? Array.from({ length: 12 }).map((_, i) => {
            const dir = i % 2 ? 1 : -1;
            const k = easeOut(clamp(dust / 16));
            return <circle key={i} cx={1590 + dir * (40 + rnd(15, i) * 160) * k} cy={SW_BOTTOM - 10 - rnd(16, i) * 50 * k} r={(10 + rnd(17, i) * 22) * (0.6 + k)} fill="#C9B9A6" opacity={0.5 * (1 - dust / 20)} />;
          })
        : null}
    </g>
  );
};

// ---------- the rooftop: Mo looks for Pip; Pip grows in the street behind the building ----------
const ROOF = 840; // feet on our roof deck
const STREET = 2780; // the street behind our building, far below the parapet (in the rooftop's own coordinates)

/** Giant Pip standing in the street behind our roof: drawn in the rooftop's `between` layer. */
const Giant: React.FC<{ x: number; feet: number; s: number; extra?: Partial<Pose>; rim?: string }> = ({ x, feet, s, extra = {}, rim = 'rimL' }) => (
  <Hero look={PIP} pose={{ ...basePose, x, y: feetAt(feet, s), scale: s, ...extra }} rimId={rim} shadow={0} />
);

/** Mo's head and shoulders as a dark, soft over-the-shoulder shape, about a third of the frame. */
const MoBack: React.FC<{ x: number; y: number; s: number }> = ({ x, y, s }) => (
  <Foreground blur={16}>
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M -150 240 Q -140 70 -40 40 Q 40 30 120 60 Q 190 110 200 240 Z" fill="#120D16" />
      <circle cx={10} cy={-30} r={66} fill="#16101A" />
      {[-150, -120, -90, -60, -30, 0, 30].map((deg, k) => {
        const a = (deg * Math.PI) / 180;
        return <circle key={k} cx={10 + Math.cos(a) * 58} cy={-30 + Math.sin(a) * 58} r={26} fill="#120C14" />;
      })}
      <path d="M -52 -40 Q -40 -100 20 -96" stroke="#FFB15A" strokeWidth={6} fill="none" opacity={0.45} strokeLinecap="round" />
    </g>
  </Foreground>
);

// S8: medium: Mo on the roof at dusk, looking left, then right: where is he?
export const S8: React.FC<ShotProps> = ({ t, len }) => {
  const pose = poseAt(t, [
    { f: 0, p: { x: 820, y: feetAt(ROOF, 1.0), scale: 1, yaw: -0.6, look: -1, armL: { a: 58, b: 52 }, armR: { a: 58, b: 52 }, headTilt: -3 } },
    { f: 18, p: { headTilt: -5 } },
    { f: 27, p: { yaw: 0.55, look: 1, headTilt: 3, armL: { a: 66, b: 62 }, armR: { a: 66, b: 62 } }, ease: easeInOut },
    { f: 52, p: { headTilt: 5 } },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 870], [len, 890]]), 600, kf(t, [[0, 1.68], [len, 1.76]]))}>
      <Rooftop t={t + 20} sunX={1250} sunY={610} />
      <Hero look={MO} pose={{ ...pose, ...faceAt(t, [[0, 'worried'], [25, 'neutral']]) }} rimId={pose.yaw > 0 ? 'rimR' : 'rimL'} shadow={0.6} />
    </g>
  );
};

// S9: wide, low: « Grandis. » Behind the parapet, in front of the sun, a giant hood rises; Mo hasn't seen it
export const S9: React.FC<ShotProps> = ({ t, len }) => {
  const g = growth(t, 14, 4.8, 5.7, 6);
  const glow = clamp((t - 12) / 4) * (1 - clamp((t - 22) / 8));
  return (
    <g transform={camT(960, kf(t, [[0, 545], [len, 530]]), kf(t, [[0, 1.0], [len, 1.04]]))}>
      <Rooftop
        t={t + 72}
        sunX={760}
        sunY={640}
        low={70}
        between={
          <g>
            <Glow x={760} y={790} r={520} o={0.5 * glow} />
            <Giant x={760} feet={STREET} s={g.scale} extra={{ squash: g.squash, yaw: 0.1 }} rim="rimR" />
          </g>
        }
      />
      <Hero look={MO} pose={{ ...basePose, x: 1520, y: feetAt(905, 1.25), scale: 1.25, yaw: 0.6, look: 1, armL: { a: 58, b: 52 }, armR: { a: 58, b: 52 }, ...faceAt(t, [[0, 'neutral']]) }} rimId="rimL" shadow={0.6} />
    </g>
  );
};

// S10: over Mo's shoulder: « Encore. » Pip's face rises over the city, the sun behind his head
export const S10: React.FC<ShotProps> = ({ t, len }) => {
  const g = growth(t, 17, 5.7, 7.2, 6);
  return (
    <g transform={camT(kf(t, [[0, 900], [len, 910]]), kf(t, [[0, 525], [len, 505]]), kf(t, [[0, 1.0], [len, 1.05]]))}>
      <Rooftop
        t={t + 95}
        sunX={830}
        sunY={520}
        low={60}
        between={<Giant x={830} feet={STREET} s={g.scale} extra={{ squash: g.squash, yaw: 0.12, look: 0.7, glint: g.glint, glintColor: GOLD, expr: 'happy' }} rim="rimL" />}
      />
      <MoBack x={1560} y={860} s={3.4} />
    </g>
  );
};

/** The street far below, seen from high above: dark blocks, lit windows, street lights, a car or two. */
const StreetBelow: React.FC<{ t: number }> = ({ t }) => (
  <g>
    <rect x={-1000} y={-800} width={3920} height={2700} fill="#120E1A" />
    <g filter="url(#blur6)">
      {Array.from({ length: 30 }).map((_, i) => {
        const x = -700 + (i % 6) * 560 + rnd(21, i) * 80;
        const y = -500 + Math.floor(i / 6) * 420 + rnd(22, i) * 60;
        return (
          <g key={i}>
            <rect x={x} y={y} width={380 + rnd(23, i) * 80} height={260 + rnd(24, i) * 60} fill={i % 3 ? '#231A2E' : '#1C1626'} />
            {Array.from({ length: 4 }).map((__, k) => (
              <rect key={k} x={x + 30 + rnd(25, i * 7 + k) * 300} y={y + 30 + rnd(26, i * 7 + k) * 180} width={34} height={22} fill="#FFC27A" opacity={rnd(27, i + k) > 0.5 ? 0.55 : 0.15} />
            ))}
          </g>
        );
      })}
      {Array.from({ length: 10 }).map((_, i) => (
        <circle key={`sl${i}`} cx={-600 + i * 420} cy={1500 - (i % 2) * 40} r={22} fill="#FFD9A0" opacity={0.8} />
      ))}
      <circle cx={-200 + ((t * 9) % 2400)} cy={1480} r={14} fill="#FF4A4A" opacity={0.9} />
      <circle cx={2200 - ((t * 7) % 2400)} cy={1560} r={14} fill="#FFF3C4" opacity={0.9} />
    </g>
  </g>
);

// S11: high angle, from up where his head is now: « Encore. » The roof far below, Mo tiny, looking up into Pip's shadow
/** POV from his head, looking down: the hood's edge and the two drawstrings hanging into the top of frame. */
const HoodPOV: React.FC<{ t: number }> = ({ t }) => {
  const sw = Math.sin(t / 5) * 18;
  return (
    <g>
      <Foreground blur={16}>
        <path d="M -200 -100 L 2120 -100 L 2120 60 Q 960 200 -200 60 Z" fill="#14111C" />
      </Foreground>
      {[700, 1220].map((x, i) => {
        const dx = sw * (i ? -1 : 1);
        return (
          <g key={i} filter="url(#blur6)">
            <path d={`M ${x} -40 Q ${x + dx * 0.5} 160 ${x + dx} 330`} stroke="#E9B13A" strokeWidth={30} fill="none" strokeLinecap="round" />
            <ellipse cx={x + dx} cy={350} rx={26} ry={34} fill="#C98E28" />
          </g>
        );
      })}
    </g>
  );
};

export const S11: React.FC<ShotProps> = ({ t, len }) => {
  const k = easeOut(clamp((t - 17) / 8));
  const z = 1.2 - 0.3 * k + 0.02 * Math.sin(t / 3) * (1 - k);
  const shade = 0.25 + 0.4 * k;
  const roof = '560,300 1360,300 1600,980 320,980';
  return (
    <g transform={`translate(960 640) scale(${z}) rotate(${-3 + 2 * k}) translate(-960 -640)`}>
      <StreetBelow t={t} />
      {/* our roof from above: the deck, the parapet round it, the clutter, the string lights */}
      <polygon points="540,284 1380,284 1626,996 294,996" fill="#3A3040" />
      <polygon points={roof} fill="#2A2232" />
      {Array.from({ length: 60 }).map((_, i) => (
        <circle key={i} cx={420 + rnd(31, i) * 1080} cy={330 + rnd(32, i) * 620} r={2 + rnd(33, i) * 3} fill="#221B29" />
      ))}
      <path d="M 540 284 L 294 996" stroke="#FFB15A" strokeWidth={6} opacity={0.55} />
      <g>
        <polygon points="410,360 610,360 630,520 400,520" fill="#3A3444" />
        <circle cx={515} cy={440} r={52} fill="#2A2532" />
        <path d="M 470 440 L 560 440 M 515 395 L 515 485" stroke="#3A3444" strokeWidth={8} />
      </g>
      {[1180, 1260, 1330].map((x, i) => (
        <g key={i}>
          <circle cx={x + 30} cy={340 + i * 8} r={26} fill="#8A5040" />
          <circle cx={x + 30} cy={340 + i * 8} r={18} fill="#4E7350" />
        </g>
      ))}
      <path d="M 360 880 Q 960 640 1560 880" stroke="#120C18" strokeWidth={4} fill="none" />
      {Array.from({ length: 13 }).map((_, i) => {
        const u = i / 12;
        const x = 360 + u * 1200;
        const y = 880 - Math.sin(u * Math.PI) * 120;
        return (
          <g key={`b${i}`}>
            <circle cx={x} cy={y} r={7} fill="#FFE2B0" />
            <Glow x={x} y={y} r={40} o={0.7} />
          </g>
        );
      })}
      {/* Pip's shadow falls over the roof as he grows */}
      <g filter="url(#blur16)">
        <ellipse cx={kf(t, [[0, 700], [len, 760]])} cy={260} rx={420 + 260 * k} ry={300 + 200 * k} fill="#05030A" opacity={shade} />
      </g>
      {/* Mo, tiny, looking straight up at us */}
      <g transform={`translate(1000 700) scale(1 0.84) translate(-1000 -700)`}>
        <Hero look={MO} pose={{ ...basePose, x: 1000, y: feetAt(700, 0.5), scale: 0.5, yaw: 0, look: 0, armL: { a: 40, b: 30 }, armR: { a: 40, b: 30 }, ...faceAt(t, [[0, 'shock']]) }} rimId="rimL" shadow={1} />
      </g>
      <Glow x={960} y={180} r={420} o={0.35 * (1 - k)} />
      <HoodPOV t={t} />
    </g>
  );
};

// S12: close-up: Mo, frozen; behind him, out of focus, the giant face looking down at him
export const S12: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 3.3 * (1 + 0.04 * clamp(t / len));
  const head = { x: 1230, y: 610 };
  const pose: Pose = {
    ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: kf(t, [[0, 0.3], [10, -0.3]]), look: kf(t, [[0, 0.6], [9, -1], [40, -0.7]]), headTilt: kf(t, [[0, 0], [12, -6]]),
    armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'neutral'], [8, 'shock']]),
  };
  return (
    <g>
      <g filter="url(#blur16)">
        <g transform="translate(-480 -560) scale(1.9)">
          <Rooftop t={t + 130} sunX={700} sunY={540} low={60} between={<Giant x={700} feet={STREET} s={7.4} extra={{ yaw: 0.25, look: 1, expr: 'happy' }} rim="rimL" />} />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.42} />
      <Hero look={MO} pose={pose} rimId="rimL" shadow={0} />
    </g>
  );
};

// ---------- the city: Pip as a giant among the buildings ----------
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
      <TitleCard t={t} lines={['ET SI TU POUVAIS', 'GRANDIR À VOLONTÉ ?']} accent="GRANDIR" accentT={40} size={100} y={150} />
    </g>
  );
};

/** Pigeons circling a point, flapping. */
const Pigeons: React.FC<{ x: number; y: number; t: number; rx: number; ry: number; n?: number }> = ({ x, y, t, rx, ry, n = 5 }) => (
  <g>
    {Array.from({ length: n }).map((_, i) => {
      const a = t / 7 + (i * Math.PI * 2) / n;
      const bx = x + Math.cos(a) * rx * (0.8 + 0.2 * rnd(41, i));
      const by = y + Math.sin(a) * ry + Math.sin(t / 3 + i) * 10;
      const fl = Math.sin(t / 1.6 + i * 1.3) * 12;
      const sz = 1.4 + 0.6 * Math.sin(a);
      return (
        <path key={i} transform={`translate(${bx} ${by}) scale(${sz})`} d={`M -14 ${fl * 0.4} Q -7 ${-6 + fl} 0 0 Q 7 ${-6 + fl} 14 ${fl * 0.4}`} stroke="#2A1A30" strokeWidth={4} fill="none" strokeLinecap="round" />
      );
    })}
  </g>
);

// S14: medium, low: « Génial, non ? » Giant Pip leans on a tower like a bar counter; the shades drop on
export const S14: React.FC<ShotProps> = ({ t, len }) => {
  const s = 3.3;
  const pose = poseAt(t, [
    { f: 0, p: { x: 700, y: feetAt(1080, s), scale: s, yaw: 0.45, look: 0.6, tilt: 7, headTilt: 3, armL: { a: 20, b: 12 }, armR: { a: 78, b: 18 } } },
    { f: 10, p: { headTilt: -3, look: 0.1 } },
    { f: 22, p: { headTilt: 4, tilt: 9 } },
  ]);
  const j = joints(pose);
  const elbow = toWorld(pose, j.armR.mid);
  const hand = toWorld(pose, j.armR.end);
  const top = Math.max(elbow.y, hand.y) + 6 * s;
  const tower = { x0: elbow.x - 40, x1: elbow.x + 420 };
  const glasses = easeOut(clamp((t - 21) / 6));
  return (
    <g transform={camT(kf(t, [[0, 960], [len, 980]]), kf(t, [[0, 520], [len, 505]]), kf(t, [[0, 1.0], [len, 1.05]]))}>
      <Rooftop
        t={t + 60}
        sunX={430}
        sunY={640}
        low={300}
        strings={false}
        between={
          <g>
            <rect x={tower.x0} y={top} width={tower.x1 - tower.x0} height={1400} fill="#3A2C55" />
            <rect x={tower.x0 + (tower.x1 - tower.x0) * 0.62} y={top} width={(tower.x1 - tower.x0) * 0.38} height={1400} fill="#2C2244" />
            <rect x={tower.x0 - 12} y={top - 16} width={tower.x1 - tower.x0 + 24} height={22} fill="#4A3A66" />
            <path d={`M ${tower.x0 - 12} ${top - 16} L ${tower.x1 + 12} ${top - 16}`} stroke="#FFB15A" strokeWidth={4} opacity={0.7} />
            <path d={`M ${tower.x0} ${top} L ${tower.x0} ${top + 1400}`} stroke="#FFB15A" strokeWidth={5} opacity={0.6} />
            {Array.from({ length: 5 }).map((_, c) =>
              Array.from({ length: 9 }).map((__, r) => {
                const q = rnd(81, c * 13 + r);
                return q > 0.35 ? <rect key={`tw${c}-${r}`} x={tower.x0 + 40 + c * 60} y={top + 50 + r * 70} width={26} height={36} fill={q > 0.85 ? '#9FC0FF' : '#FFC27A'} opacity={0.5 + q * 0.4} /> : null;
              }),
            )}
            <path d={`M ${tower.x0 + 220} ${top} L ${tower.x0 + 220} ${top - 90}`} stroke="#2A2040" strokeWidth={8} />
            <circle cx={tower.x0 + 220} cy={top - 92} r={6} fill="#FF4A4A" />
            <Hero look={PIP} pose={{ ...pose, glasses, ...faceAt(t, [[0, 'happy'], [24, 'cool']]) }} rimId="rimL" shadow={0} />
          </g>
        }
      />
      <Pigeons x={tower.x0 + 200} y={top + 300 - kf(t, [[0, 90], [len, 120]])} t={t + 10} rx={300} ry={80} n={6} />
      {t > 27 ? <Sparkle x={pose.x + 80} y={pose.y + 300 - 190 * s} t={t - 27} s={1.3} /> : null}
    </g>
  );
};

// S15: extreme close-up: « Un détail : » the smile drops off the giant face
export const S15: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 6.4 * (1 + 0.035 * clamp(t / len));
  const head = { x: 960, y: 650 };
  const pose: Pose = {
    ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: 0.1, look: kf(t, [[0, 0.2], [14, -0.4]]), headTilt: kf(t, [[0, 0], [16, -4]]),
    armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'happy'], [6, 'neutral'], [15, 'worried']]),
  };
  return (
    <g>
      <g filter="url(#blur16)">
        <g transform="translate(-560 -640) scale(2)">
          <Rooftop t={t + 200} sunX={1180} sunY={600} low={320} />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.22} />
      <Hero look={PIP} pose={pose} rimId="rimR" shadow={0} />
    </g>
  );
};
// ---------- the turn: the schematic, then the step ----------
const fr = (v: number) => Math.round(v).toLocaleString('en-US').replace(/,/g, ' ');

/** A cube in oblique projection: front face at (x, y) (top-left), side `a`; `grid` subdivisions on each face. */
const Cube: React.FC<{ x: number; y: number; a: number; t: number; grid?: number; color?: string }> = ({ x, y, a, t, grid = 0, color = SCH.line }) => {
  const d = a * 0.38;
  const outline = `M ${x} ${y} L ${x + a} ${y} L ${x + a} ${y + a} L ${x} ${y + a} Z M ${x} ${y} L ${x + d} ${y - d} L ${x + a + d} ${y - d} L ${x + a} ${y} M ${x + a + d} ${y - d} L ${x + a + d} ${y + a - d} L ${x + a} ${y + a}`;
  const g = clamp((t - 10) / 10);
  const lines: string[] = [];
  for (let i = 1; i < grid; i++) {
    const k = i / grid;
    lines.push(`M ${x + a * k} ${y} L ${x + a * k} ${y + a}`, `M ${x} ${y + a * k} L ${x + a} ${y + a * k}`); // front
    lines.push(`M ${x + a * k} ${y} L ${x + a * k + d} ${y - d}`, `M ${x + d * k} ${y - d * k} L ${x + a + d * k} ${y - d * k}`); // top
    lines.push(`M ${x + a + d * k} ${y - d * k} L ${x + a + d * k} ${y + a - d * k}`, `M ${x + a} ${y + a * k} L ${x + a + d} ${y + a * k - d}`); // side
  }
  return (
    <g>
      <path d={`M ${x} ${y} L ${x + a} ${y} L ${x + a} ${y + a} L ${x} ${y + a} Z`} fill={color} opacity={0.06} />
      {grid > 1 && g > 0 ? <path d={lines.join(' ')} stroke={color} strokeWidth={1.6} opacity={0.45 * g} fill="none" /> : null}
      <DrawOn d={outline} t={t} dur={10} color={color} width={4} />
    </g>
  );
};

/** Pip as a line drawing (the schematic's figure): hood, head, body, legs. x, y is between the feet; h his height. */
const Figure: React.FC<{ x: number; y: number; h: number; t: number; color?: string }> = ({ x, y, h, t, color = SCH.line }) => {
  const k = h / 400;
  const d = `M ${x - 30 * k} ${y} L ${x - 12 * k} ${y - 140 * k} L ${x + 12 * k} ${y - 140 * k} L ${x + 30 * k} ${y} M ${x - 40 * k} ${y - 140 * k} L ${x - 44 * k} ${y - 252 * k} Q ${x} ${y - 262 * k} ${x + 44 * k} ${y - 252 * k} L ${x + 40 * k} ${y - 140 * k} Z M ${x - 44 * k} ${y - 248 * k} L ${x - 60 * k} ${y - 150 * k} M ${x + 44 * k} ${y - 248 * k} L ${x + 60 * k} ${y - 150 * k}`;
  return (
    <g>
      <DrawOn d={d} t={t} dur={10} color={color} width={Math.max(3, 4 * Math.min(1, k * 2))} />
      {t > 3 ? <circle cx={x} cy={y - 330 * k} r={62 * k} fill="none" stroke={color} strokeWidth={Math.max(3, 4 * Math.min(1, k * 2))} opacity={clamp((t - 3) / 5)} /> : null}
      {t > 3 ? <path d={`M ${x - 70 * k} ${y - 316 * k} Q ${x - 80 * k} ${y - 404 * k} ${x} ${y - 410 * k} Q ${x + 80 * k} ${y - 404 * k} ${x + 70 * k} ${y - 316 * k}`} fill="none" stroke={color} strokeWidth={Math.max(3, 4 * Math.min(1, k * 2))} opacity={clamp((t - 3) / 5)} /> : null}
    </g>
  );
};

// S16: schematic: « dix fois plus grand, c'est mille fois plus lourd » - ×10 in height, one cube becomes a thousand
export const S16: React.FC<ShotProps> = ({ t, len }) => (
  <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
    <Schematic t={t} id="sch16" />
    {/* two Pips to scale on a baseline: 1 and 10 */}
    <DrawOn d="M 170 900 L 900 900" t={t} dur={8} color={SCH.dim} width={3} />
    <Figure x={260} y={900} h={64} t={t - 2} />
    <Figure x={610} y={900} h={640} t={t - 6} color={GOLD} />
    <Arrow x0={790} y0={900} x1={790} y1={268} t={t - 16} dur={10} color={SCH.live} bend={0} />
    <SchLabel x={260} y={960} t={t - 4} text="×1" size={40} color={SCH.dim} />
    <SchLabel x={610} y={960} t={t - 14} text="TAILLE ×10" size={46} color={GOLD} />
    {/* one cube, then the cube ten times as big: a thousand of the first */}
    <Cube x={1040} y={760} a={40} t={t - 30} />
    <SchLabel x={1060} y={850} t={t - 32} text="1" size={36} color={SCH.dim} />
    <Arrow x0={1120} y0={780} x1={1190} y1={720} t={t - 34} dur={6} />
    <Cube x={1230} y={420} a={400} t={t - 36} grid={10} color={GOLD} />
    <SchLabel x={1500} y={240} t={t - 40} text="POIDS" size={40} color={SCH.dim} />
    <CountUp x={1500} y={960} t={t - 40} to={1000} dur={22} size={92} format={(v) => `×${fr(Math.max(1, v))}`} />
  </g>
);

// S17: schematic: « Mais tes os ne sont que cent fois plus solides » - the bone's section ×100, so each cm² carries ×10
export const S17: React.FC<ShotProps> = ({ t, len }) => {
  const r1 = 22;
  const r2 = 220;
  const fill = clamp((t - 36) / 22);
  const cells: React.ReactNode[] = [];
  for (let i = 0; i < 10; i++)
    for (let k = 0; k < 10; k++) {
      const n = i * 10 + k;
      if (n < fill * 100) cells.push(<rect key={n} x={700 - r2 + k * 44 + 3} y={560 - r2 + i * 44 + 3} width={38} height={38} rx={4} fill={GOLD} opacity={0.35} />);
    }
  return (
    <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
      <Schematic t={t + 74} id="sch17" />
      {/* a femur, then its cross-section, ten times wider: a hundred times the area */}
      <DrawOn d="M 150 330 q -36 -40 0 -64 q 30 -14 44 18 L 330 230 q 14 -32 44 -18 q 36 24 0 64 q 36 40 0 64 q -30 14 -44 -18 L 194 380 q -14 32 -44 18 q -36 -24 0 -64 Z" t={t - 2} dur={12} color={SCH.line} width={4} />
      <SchLabel x={262} y={460} t={t - 8} text="FÉMUR" size={34} color={SCH.dim} />
      <circle cx={262} cy={600} r={r1} fill="none" stroke={SCH.line} strokeWidth={4} opacity={clamp((t - 10) / 5)} />
      <SchLabel x={262} y={680} t={t - 12} text="SECTION ×1" size={30} color={SCH.dim} />
      <Arrow x0={310} y0={600} x1={440} y1={600} t={t - 16} dur={6} />
      <defs>
        <clipPath id="s17sec">
          <circle cx={700} cy={560} r={r2} />
        </clipPath>
      </defs>
      <g clipPath="url(#s17sec)">{cells}</g>
      {t > 20 ? <circle cx={700} cy={560} r={r2 * easeOut(clamp((t - 20) / 10))} fill="none" stroke={GOLD} strokeWidth={6} /> : null}
      <SchLabel x={700} y={850} t={t - 30} text="SOLIDITÉ" size={40} color={SCH.dim} />
      <CountUp x={700} y={950} t={t - 38} to={100} dur={18} size={84} format={(v) => `×${Math.max(1, Math.round(v))}`} />
      {/* the sum that breaks him: a thousand times the weight on a hundred times the bone */}
      <SchLabel x={1450} y={330} t={t - 46} text="POIDS ×1 000" size={54} color={SCH.line} />
      <DrawOn d="M 1240 380 L 1660 380" t={t - 50} dur={6} color={SCH.dim} width={4} />
      <SchLabel x={1450} y={450} t={t - 50} text="OS ×100" size={54} color={SCH.line} />
      <SchLabel x={1450} y={600} t={t - 56} text="= ×10 PAR cm²" size={60} color={SCH.live} />
      {t > 68 ? (
        <g transform="translate(1450 760)">
          <path d="M -120 0 L 120 0" stroke={UI.bad} strokeWidth={10} strokeLinecap="round" />
          <DrawOn d="M -20 -40 L 6 -8 L -12 6 L 18 44" t={t - 68} dur={4} color={UI.bad} width={9} />
        </g>
      ) : null}
    </g>
  );
};

/** A street of buildings at dusk with room for a giant: sky, sun, the far skyline, a row of houses he can stride over. */
const StreetSet: React.FC<{ t: number; id: string; red?: number; sunX?: number; sunY?: number; children?: React.ReactNode; front?: React.ReactNode }> = ({ t, id, red = 0, sunX = 1300, sunY = 600, children, front }) => (
  <g>
    <DuskSky id={`${id}sky`} horizonY={900} red={red} />
    <Sun x={sunX} y={sunY} r={150} t={t} red={red} />
    <g filter="url(#blur6)" opacity={1 - red * 0.6}>
      {[[300, 260, 360, 24], [1320, 200, 420, 30], [900, 380, 300, 18]].map(([cx, cy, rx, ry], i) => (
        <ellipse key={i} cx={cx + ((t * 0.3) % 60)} cy={cy} rx={rx} ry={ry} fill="#6A3E6E" opacity={0.7} />
      ))}
    </g>
    <Skyline y={880} seed={9} color={red > 0.5 ? '#3A1222' : '#4A3260'} h={240} />
    <Haze y={860} h={200} o={0.3 * (1 - red)} />
    {children}
    {/* the row of houses in front of him: roofs, lit windows, a street light */}
    {[
      [-200, 250, 300], [100, 300, 240], [430, 280, 320], [760, 330, 260], [1120, 260, 300], [1430, 300, 220], [1760, 320, 280],
    ].map(([x, w, h], i) => (
      <g key={i}>
        <rect x={x} y={1080 - h} width={w} height={h} fill={red > 0.5 ? '#1E0A14' : i % 2 ? '#2A2038' : '#251C33'} />
        <path d={`M ${x - 10} ${1080 - h} L ${x + w / 2} ${1080 - h - 60} L ${x + w + 10} ${1080 - h} Z`} fill={red > 0.5 ? '#16060E' : '#1E1628'} />
        <path d={`M ${x + w / 2} ${1080 - h - 60} L ${x + w + 10} ${1080 - h}`} stroke="#FFB15A" strokeWidth={3} opacity={0.4 * (1 - red)} />
        {Array.from({ length: 4 }).map((_, k) => {
          const q = rnd(91, i * 7 + k);
          return q > 0.35 ? <rect key={k} x={x + 30 + (k % 2) * (w - 100)} y={1080 - h + 50 + Math.floor(k / 2) * 90} width={40} height={50} fill="#FFC27A" opacity={(0.5 + q * 0.4) * (1 - red * 0.6)} /> : null;
        })}
      </g>
    ))}
    {front}
    {red > 0 ? <rect x={-400} y={-400} width={2720} height={1900} fill="#16000A" opacity={0.35 * red} /> : null}
  </g>
);

// S18: wide, low: « Au premier pas, ils cassent. » He lifts a foot over the houses, puts it down: CRAC
export const S18: React.FC<ShotProps> = ({ t, len }) => {
  const s = 2.0;
  const hit = 50;
  const pose = poseAt(t, [
    { f: 0, p: { x: 860, y: feetAt(915, s), scale: s, yaw: 0.85, facing: 1, look: 0.6, legL: { a: 6, b: 0 }, legR: { a: -4, b: 0 }, armL: { a: 20, b: 12 }, armR: { a: 24, b: 14 } } },
    { f: 10, p: { tilt: -4, legL: { a: 70, b: -70 }, armL: { a: 36, b: 20 }, armR: { a: 50, b: 30 } }, ease: easeOut },
    { f: 30, p: { tilt: 4, legL: { a: 46, b: -10 }, x: 900 } },
    { f: hit - 2, p: { tilt: 8, legL: { a: 34, b: 0 }, x: 930 } },
    { f: hit + 2, p: { tilt: 14, headTilt: 10, legL: { a: 44, b: -30 }, legR: { a: -10, b: -36 }, armL: { a: 70, b: 40 }, armR: { a: 80, b: 50 } }, ease: easeOut },
    { f: hit + 7, p: { tilt: 18, headTilt: 12, squash: 0.08 } },
  ]);
  const flash = t >= hit && t < hit + 3;
  return (
    <g transform={camT(980, kf(t, [[0, 560], [len, 580]]), kf(t, [[0, 1.0], [len, 1.06]]))}>
      <StreetSet t={t} id="st18" red={t >= hit ? 0.35 : 0}>
        <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'neutral'], [12, 'happy'], [hit, 'shock']]) }} rimId={t >= hit ? 'rimRed' : 'rimR'} shadow={0} />
      </StreetSet>
      {flash ? (
        <g>
          {(() => {
            const j = joints(pose);
            const k = toWorld(pose, j.legL.mid);
            return <path d={`M ${k.x - 50} ${k.y - 60} L ${k.x + 10} ${k.y - 10} L ${k.x - 20} ${k.y + 10} L ${k.x + 50} ${k.y + 70}`} stroke="#FF4A4A" strokeWidth={12} fill="none" strokeLinejoin="round" />;
          })()}
        </g>
      ) : null}
    </g>
  );
};

// S19: wide: « C'est réel. » He sits down on a building, holding his leg; the sky goes red (Haldane's giants sat down too)
export const S19: React.FC<ShotProps> = ({ t, len }) => {
  const s = 2.3;
  const seat = { x: 1180, y: 700 };
  const pose = poseAt(t, [
    { f: 0, p: { x: seat.x, y: seat.y, scale: s, yaw: -0.85, facing: -1, look: -0.4, tilt: -6, headTilt: -8, legL: { a: 82, b: -78 }, legR: { a: 76, b: -60 }, armL: { a: 40, b: -30 }, armR: { a: 30, b: -20 } } },
    { f: 20, p: { headTilt: -4 } },
    { f: 40, p: { headTilt: -10 } },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 980], [len, 1010]]), kf(t, [[0, 560], [len, 570]]), kf(t, [[0, 1.0], [len, 1.08]]))}>
      <StreetSet
        t={t + 60}
        id="st19"
        red={kf(t, [[0, 0.45], [len, 0.85]])}
        sunX={700}
        sunY={640}
        front={
          <g>
            {/* the block he sits on, nearer than the houses */}
            <rect x={seat.x - 140} y={seat.y} width={520} height={600} fill="#1A0A12" />
            <rect x={seat.x - 140} y={seat.y} width={520} height={14} fill="#2A1420" />
            <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'worried']]) }} rimId="rimRed" shadow={0} />
          </g>
        }
      />
    </g>
  );
};

// ---------- the next day: the kitchen ----------
/** A plaster cast from the knee to the foot, drawn over the rig's near leg. */
const LegCast: React.FC<{ pose: Pose; leg: 'legL' | 'legR' }> = ({ pose, leg }) => {
  const j = joints(pose)[leg];
  const a = toWorld(pose, j.mid);
  const b = toWorld(pose, j.end);
  const w = 26 * pose.scale;
  return (
    <g>
      <path d={`M ${a.x} ${a.y} L ${b.x} ${b.y}`} stroke="#14121C" strokeWidth={w + 8 * pose.scale} strokeLinecap="round" />
      <path d={`M ${a.x} ${a.y} L ${b.x} ${b.y}`} stroke="#F2EEE6" strokeWidth={w} strokeLinecap="round" />
      <path d={`M ${a.x + (b.x - a.x) * 0.35 - 6 * pose.scale} ${a.y + (b.y - a.y) * 0.35} l ${10 * pose.scale} ${4 * pose.scale} l ${-4 * pose.scale} ${6 * pose.scale}`} stroke="#4A7AA0" strokeWidth={2.5 * pose.scale} fill="none" />
      <path d={`M ${a.x + (b.x - a.x) * 0.6 - 5 * pose.scale} ${a.y + (b.y - a.y) * 0.6} q ${6 * pose.scale} ${-6 * pose.scale} ${10 * pose.scale} 0`} stroke="#D9534F" strokeWidth={2.5 * pose.scale} fill="none" />
    </g>
  );
};

/** A crutch from under the near arm to the floor. */
const Crutch: React.FC<{ pose: Pose; floor: number; dx?: number }> = ({ pose, floor, dx = 40 }) => {
  const j = joints(pose);
  const top = toWorld(pose, { x: j.armR.root.x + 6, y: j.armR.root.y + 18 });
  const foot = { x: top.x + dx * pose.scale, y: floor };
  const grip = { x: top.x + (foot.x - top.x) * 0.4, y: top.y + (foot.y - top.y) * 0.4 };
  const k = pose.scale;
  return (
    <g>
      <path d={`M ${top.x - 10 * k} ${top.y} L ${foot.x} ${foot.y} M ${top.x + 10 * k} ${top.y} L ${foot.x} ${foot.y}`} stroke="#9AA0A8" strokeWidth={5 * k} strokeLinecap="round" />
      <rect x={top.x - 18 * k} y={top.y - 5 * k} width={36 * k} height={10 * k} rx={5 * k} fill="#2A2A30" />
      <rect x={grip.x - 14 * k} y={grip.y - 4 * k} width={28 * k} height={8 * k} rx={4 * k} fill="#2A2A30" />
      <ellipse cx={foot.x} cy={foot.y} rx={8 * k} ry={4 * k} fill="#2A2A30" />
    </g>
  );
};

const SUIT_AT = stand(KITCHEN, 0.6, 0.4);
const MOM_AT = stand(KITCHEN, 0.84, 0.3);
const PIP_IN = stand(KITCHEN, 0.14, 0.66);

// S20: wide: « Le lendemain, un homme en... » Pip hobbles in on a crutch, his leg in plaster; a man in a suit is waiting
export const S20: React.FC<ShotProps> = ({ t, len }) => {
  const floor = PIP_IN.y + LEG_LEN * PIP_IN.scale;
  const walk = Math.min(t, 26);
  const pip = { ...basePose, x: PIP_IN.x - 120 + walk * 4.2, y: PIP_IN.y - Math.abs(Math.sin(walk / 4)) * 6, scale: PIP_IN.scale, yaw: 0.55, look: 0.8, legL: { a: 12 * Math.sin(walk / 4), b: -10 }, legR: { a: 4, b: 0 }, armL: { a: 16, b: -6 }, armR: { a: 30, b: 20 }, ...faceAt(t, [[0, 'neutral'], [30, 'worried']]) } as Pose;
  const suit = poseAt(t, [{ f: 0, p: { x: SUIT_AT.x, y: SUIT_AT.y, scale: SUIT_AT.scale, yaw: -0.45, look: -0.8, armL: { a: 8, b: -6 }, armR: { a: 8, b: -6 } } }]);
  const mom = poseAt(t, [{ f: 0, p: { x: MOM_AT.x, y: MOM_AT.y, scale: MOM_AT.scale, yaw: -0.4, look: -0.6, armL: { a: 30, b: 70 }, armR: { a: 30, b: 70 } } }]);
  return (
    <g transform={camT(kf(t, [[0, 940], [len, 920]]), 560, kf(t, [[0, 1.0], [len, 1.05]]))}>
      <Kitchen t={t + 300} id="k20" veil={0.38} />
      <Hero look={MOM} pose={{ ...mom, ...faceAt(t, [[0, 'worried']]) }} rimId="rimL" shadow={0.6} />
      <Hero look={SUIT} pose={{ ...suit, ...faceAt(t, [[0, 'neutral']]) }} rimId="rimL" shadow={0} />
      <KitchenIsland />
      <Crutch pose={pip} floor={floor} />
      <Hero look={PIP} pose={pip} rimId="rimR" shadow={0.8} />
      <LegCast pose={pip} leg="legR" />
    </g>
  );
};

/** A photo print: a giant hooded silhouette over a city at dusk, two gold eyes. x, y its centre. */
const Photo: React.FC<{ x: number; y: number; w: number; rot?: number }> = ({ x, y, w, rot = 0 }) => {
  const h = w * 1.18;
  const iw = w * 0.86;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot})`}>
      <rect x={-w / 2 + 6} y={-h / 2 + 8} width={w} height={h} fill="#000" opacity={0.35} />
      <rect x={-w / 2} y={-h / 2} width={w} height={h} fill="#F2EEE6" />
      <defs>
        <clipPath id="photoClip">
          <rect x={-iw / 2} y={-h / 2 + w * 0.07} width={iw} height={iw} />
        </clipPath>
      </defs>
      <g clipPath="url(#photoClip)">
        <rect x={-iw / 2} y={-h / 2 + w * 0.07} width={iw} height={iw} fill="#6E3A6E" />
        <rect x={-iw / 2} y={-h / 2 + w * 0.07 + iw * 0.55} width={iw} height={iw * 0.45} fill="#F2985A" />
        <circle cx={iw * 0.05} cy={-h / 2 + w * 0.07 + iw * 0.45} r={iw * 0.33} fill="#1A1424" />
        <circle cx={iw * 0.05} cy={-h / 2 + w * 0.07 + iw * 0.5} r={iw * 0.24} fill="#E6DCCB" />
        <circle cx={iw * -0.03} cy={-h / 2 + w * 0.07 + iw * 0.47} r={iw * 0.03} fill={GOLD} />
        <circle cx={iw * 0.13} cy={-h / 2 + w * 0.07 + iw * 0.47} r={iw * 0.03} fill={GOLD} />
        {Array.from({ length: 8 }).map((_, i) => (
          <rect key={i} x={-iw / 2 + i * iw * 0.13} y={-h / 2 + w * 0.07 + iw * (0.72 + rnd(95, i) * 0.12)} width={iw * 0.13} height={iw} fill="#2A2038" />
        ))}
      </g>
      <text x={0} y={h / 2 - w * 0.07} textAnchor="middle" fontFamily={FONT.hand} fontSize={w * 0.1} fill="#3A3444">
        hier, 19 h 42
      </text>
    </g>
  );
};

// S21: medium, low: « costume t'attend dans la cuisine. » The man in the suit slides a photo across the island
export const S21: React.FC<ShotProps> = ({ t, len }) => {
  const slide = easeOut(clamp((t - 8) / 14));
  const ph = islandTop(0.5, 0.7);
  const suit = poseAt(t, [
    { f: 0, p: { x: SUIT_AT.x, y: SUIT_AT.y, scale: SUIT_AT.scale, yaw: -0.35, look: -0.5, armL: { a: 8, b: -6 }, armR: { a: 40, b: 30 } } },
    { f: 8, p: { armR: { a: 50, b: 40 } } },
    { f: 22, p: { armR: { a: 36, b: 22 }, headTilt: -3, look: -0.9 }, ease: easeOut },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 1010], [len, 1000]]), kf(t, [[0, 560], [len, 570]]), kf(t, [[0, 2.0], [len, 2.12]]))}>
      <g filter="url(#blur3)">
        <Kitchen t={t + 340} id="k21" veil={0.42} />
        <Hero look={MOM} pose={{ ...basePose, x: MOM_AT.x, y: MOM_AT.y, scale: MOM_AT.scale, yaw: -0.4, look: -0.6, armL: { a: 30, b: 70 }, armR: { a: 30, b: 70 }, expr: 'worried' }} rimId="rimL" shadow={0} />
      </g>
      <Hero look={SUIT} pose={{ ...suit, ...faceAt(t, [[0, 'neutral'], [30, 'smug']]) }} rimId="rimL" shadow={0} />
      <KitchenIsland stools={false} />
      <Photo x={ph.x + 60 - slide * 150} y={ph.y - 4} w={92} rot={-8 + slide * 14} />
      <Glow x={ph.x - 60} y={ph.y - 40} r={220} o={0.25} />
    </g>
  );
};

// S22: insert: « Et à l'étage, » the pendant starts to swing, a crack runs across the ceiling, dust comes down
export const S22: React.FC<ShotProps> = ({ t, len }) => {
  const sw = Math.sin(t / 2.4) * 11 * clamp(t / 6);
  const top = { x: 960, y: 120 };
  return (
    <g transform={`translate(${Math.sin(t * 3.1) * 4 * clamp(t / 4)} ${Math.cos(t * 2.3) * 3 * clamp(t / 4)})`}>
      <rect x={-100} y={-100} width={2120} height={1280} fill="#2A2330" />
      <path d="M -100 470 L 2020 470 L 2020 1180 L -100 1180 Z" fill="#3B4148" />
      <path d="M -100 470 L 2020 470" stroke="#231C29" strokeWidth={10} />
      <rect x={-100} y={-100} width={2120} height={570} fill="#211B28" />
      {/* the crack drawing across the ceiling */}
      <DrawOn d="M 120 380 L 300 330 L 360 360 L 560 260 L 640 300 L 820 180 L 900 200 L 1080 90 L 1180 140 L 1400 40 L 1500 70 L 1760 -20" t={t - 4} dur={18} color="#0A070E" width={9} />
      <DrawOn d="M 560 260 L 600 180 L 660 150 M 1080 90 L 1120 20 M 1400 40 L 1460 120 L 1540 140" t={t - 10} dur={12} color="#0A070E" width={6} />
      {Array.from({ length: 26 }).map((_, i) => {
        const x = 150 + rnd(51, i) * 1600;
        const y = 300 - 260 * (x / 1700) + ((t - 4) * (5 + rnd(52, i) * 7) + rnd(53, i) * 200) % 900;
        return t > 4 ? <circle key={i} cx={x} cy={y} r={2.5 + rnd(54, i) * 4} fill="#D9CDBA" opacity={0.7} /> : null;
      })}
      <g transform={`rotate(${sw} ${top.x} ${top.y})`}>
        <path d={`M ${top.x} -100 L ${top.x} ${top.y + 340}`} stroke="#120E16" strokeWidth={6} />
        <path d={`M ${top.x - 60} ${top.y + 330} L ${top.x + 60} ${top.y + 330} L ${top.x + 160} ${top.y + 450} L ${top.x - 160} ${top.y + 450} Z`} fill="#1C1620" />
        <ellipse cx={top.x} cy={top.y + 450} rx={160} ry={26} fill="#FFE2B0" />
        <path d={`M ${top.x - 150} ${top.y + 452} L ${top.x + 150} ${top.y + 452} L ${top.x + 700} ${top.y + 1400} L ${top.x - 700} ${top.y + 1400} Z`} fill="url(#g3cone)" opacity={0.4} style={{ mixBlendMode: 'screen' }} />
        <Glow x={top.x} y={top.y + 470} r={520} o={0.6} />
      </g>
    </g>
  );
};

// S23: close-up: « ta petite sœur vient de dire le mot. » Upstairs, her eyes light up gold; the room starts to shake
export const S23: React.FC<ShotProps> = ({ t, len }) => {
  const g = growth(t, 54, 2.9, 3.3, 8);
  const sc = g.scale;
  const head = { x: 900, y: 560 };
  const sh = t >= 53 ? Math.sin(t * 2.7) * 6 * clamp((t - 53) / 4) : 0;
  const pose: Pose = {
    ...basePose, x: head.x, y: head.y - HEAD.y * 2.9 + (2.9 - sc) * 60, scale: sc, yaw: 0.2, look: kf(t, [[0, 0.4], [30, -0.2], [44, 0.6]]), headTilt: kf(t, [[0, -2], [40, 4]]), sway: Math.sin(t / 4) * 10,
    armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, squash: g.squash, glint: clamp((t - 51) / 3), glintColor: GOLD, ...faceAt(t, [[0, 'smug'], [52, 'happy']]),
  };
  return (
    <g transform={`translate(${sh} 0)`}>
      <g filter="url(#blur16)">
        <g transform="translate(-700 -620) scale(2)">
          <Study t={t + 400} id="st23" />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.25} />
      {t > 51 ? <Glow x={head.x} y={head.y} r={700} o={0.35 * clamp((t - 51) / 5)} /> : null}
      <Hero look={SIS} pose={pose} rimId="rimR" shadow={0} />
      {t > 53 ? <FocusRings x={head.x} y={head.y - 60} t={(t - 53) * 1.6} r0={180} color={GOLD} /> : null}
    </g>
  );
};

// S24: close-up: « Tu montes la sauver… ou tu te tais ? » Pip looks up at the ceiling, then at the man; the light dies
export const S24: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 3.1;
  const head = { x: 1180, y: 600 };
  const swing = Math.sin(t / 2.6) * 260 * clamp(1 - t / 120);
  const dark = clamp((t - 86) / 4);
  const flick = t > 76 && t < 86 ? (rnd(77, Math.floor(t)) > 0.5 ? 1 : 0.35) : 1;
  const pose: Pose = {
    ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: kf(t, [[0, 0.15], [40, 0.15], [48, -0.35]]), look: kf(t, [[0, 0.2], [40, 0.2], [46, -1]]), headTilt: kf(t, [[0, -9], [38, -9], [46, 2]]),
    armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'shock'], [44, 'worried']]),
  };
  return (
    <g>
      <g opacity={flick}>
        <g filter="url(#blur16)">
          <g transform="translate(-1000 -480) scale(1.9)">
            <Kitchen t={t + 500} id="k24" veil={0.45} />
          </g>
        </g>
        <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.3} />
        <Glow x={1100 + swing} y={-60} r={720} o={0.5} />
        <Hero look={PIP} pose={pose} rimId="rimR" shadow={0} />
        {/* the man in the suit, close and dark, over Pip's left */}
        <Foreground blur={16}>
          <path d="M -100 1180 L -100 520 Q 120 430 360 470 Q 560 520 600 760 L 640 1180 Z" fill="#0E0F14" />
          <circle cx={250} cy={300} r={200} fill="#131218" />
          <path d="M 70 230 Q 120 90 280 100" stroke="#FFB15A" strokeWidth={8} fill="none" opacity={0.3} />
        </Foreground>
        {Array.from({ length: 10 }).map((_, i) => (
          <circle key={i} cx={700 + rnd(61, i) * 1100} cy={((t * (4 + rnd(62, i) * 6) + rnd(63, i) * 900) % 1100) - 20} r={2 + rnd(64, i) * 3} fill="#D9CDBA" opacity={0.6} />
        ))}
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#000" opacity={dark} />
    </g>
  );
};
