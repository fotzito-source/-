import React from 'react';
import {
  Hero, Pose, basePose, poseAt, faceAt, kf, clamp, easeOut, easeIn, easeInOut, rnd, settle, camT, LOOKS, LEG_LEN, HEAD, joints, toWorld, walkPose,
  Stairwell, Banister, SW, hipGround, Bedroom, bedSit, BedDuvet, LAMP, Schematic, SCH, SchLabel, CountUp, DrawOn, Arrow,
  Glow, Sparkle, TitleCard, Foreground, FocusRings, DizzyStars, Dial, Cat, FONT, UI, ShotProps, Stars, Moon,
} from '../../engine';
import { GOLD, growth, feetAt, GrowFx, StreetSet, Pigeons, LegCast, Crutch } from '../grandir/shots';

// « What if you could grow at will? Part 2 ». It picks up on Part 1's cliffhanger: Pip runs upstairs on his crutch, his
// little sister has said the word and is now the size of the house. The new cost is real too: blood is heavy, so a giant's
// heart can't lift it to her brain, and a brain without blood switches off in about ten seconds. Pip grows again, cast
// and all, to catch her. Every shot is a pure function of its clock t, and every action is placed against the end of
// its segment (len), so the edit follows whatever voice is laid in.

const PIP = LOOKS.pipHood;
const SIS = LOOKS.sis;
const MOM = LOOKS.mom;
const MO = LOOKS.mo;
const SUIT = LOOKS.suit;

// ---------- our house, from the street, with its roof broken open ----------
const HOUSE = { x0: 620, x1: 1300, eave: 660, apex: 430, hole: [800, 1120] as [number, number] };

/** Our house's front: the wall, lit windows, the door with its porch light, and the roof broken open round the hole. */
const OurHouse: React.FC<{ t: number; rattle?: number; burst?: number }> = ({ t, rattle = 0, burst = 1 }) => {
  const { x0, x1, eave, apex, hole } = HOUSE;
  const cx = (x0 + x1) / 2;
  const roofY = (x: number) => eave - (eave - apex) * (1 - Math.abs(x - cx) / ((x1 - x0) / 2 + 40));
  const jag = (a: number, b: number, seed: number) => {
    let d = '';
    for (let i = 0; i <= 8; i++) {
      const x = a + ((b - a) * i) / 8;
      d += ` L ${x} ${roofY(x) + 30 + rnd(seed, i) * 60 * burst}`;
    }
    return d;
  };
  const left = `M ${x0 - 40} ${eave} L ${hole[0]} ${roofY(hole[0])} ${jag(hole[0], hole[0] + 40, 3)} L ${hole[0] + 20} ${eave} Z`;
  const right = `M ${x1 + 40} ${eave} L ${hole[1]} ${roofY(hole[1])} ${jag(hole[1] - 40, hole[1], 4)} L ${hole[1] - 20} ${eave} Z`;
  const shake = (i: number) => (rattle > 0 ? Math.sin(t * 3.3 + i * 1.7) * 4 * rattle : 0);
  return (
    <g>
      <rect x={x0} y={eave} width={x1 - x0} height={1080 - eave + 200} fill="#3A2C48" />
      <rect x={x0 + (x1 - x0) * 0.62} y={eave} width={(x1 - x0) * 0.38} height={1080 - eave + 200} fill="#30243E" />
      <path d={`M ${x0} ${eave} L ${x0} 1300`} stroke="#FFB15A" strokeWidth={4} opacity={0.5} />
      {[[690, 740], [880, 740], [1100, 740], [690, 900], [1100, 900]].map(([x, y], i) => (
        <g key={i} transform={`translate(${shake(i)} ${shake(i + 3) * 0.5})`}>
          <rect x={x} y={y} width={110} height={110} fill="#1E1628" />
          <rect x={x + 8} y={y + 8} width={94} height={94} fill="#FFC27A" opacity={0.8} />
          <path d={`M ${x + 55} ${y + 8} L ${x + 55} ${y + 102} M ${x + 8} ${y + 55} L ${x + 102} ${y + 55}`} stroke="#1E1628" strokeWidth={6} />
          <Glow x={x + 55} y={y + 55} r={120} o={0.35} />
        </g>
      ))}
      <rect x={905} y={880} width={110} height={200} fill="#1A1222" />
      <rect x={915} y={890} width={90} height={190} fill="#5A3A3A" />
      <circle cx={990} cy={990} r={6} fill="#E9C46A" />
      <rect x={950} y={850} width={20} height={16} fill="#FFE2B0" />
      <Glow x={960} y={860} r={200} o={0.5} />
      <path d={left} fill="#241A30" stroke="#120C18" strokeWidth={6} strokeLinejoin="round" />
      <path d={right} fill="#241A30" stroke="#120C18" strokeWidth={6} strokeLinejoin="round" />
      <path d={`M ${x0 - 40} ${eave} L ${hole[0]} ${roofY(hole[0])}`} stroke="#FFB15A" strokeWidth={4} opacity={0.5} />
      <rect x={x0 - 50} y={eave - 6} width={x1 - x0 + 100} height={16} fill="#1A1222" />
    </g>
  );
};

/** The street in front of our house: the far town (StreetSet) with the sister as a giant standing inside the house. */
const HouseScene: React.FC<{ t: number; id: string; sis: Pose; red?: number; rattle?: number; burst?: number; extra?: React.ReactNode; front?: React.ReactNode }> = ({ t, id, sis, red = 0, rattle = 0, burst = 1, extra, front }) => (
  <StreetSet
    t={t}
    id={id}
    red={red}
    sunX={1560}
    sunY={620}
    front={
      <g>
        <Glow x={960} y={HOUSE.apex + 120} r={420} o={0.45} />
        <Hero look={SIS} pose={sis} rimId="rimR" shadow={0} />
        {extra}
        <OurHouse t={t} rattle={rattle} burst={burst} />
        {front}
      </g>
    }
  />
);
/** The sister standing in the house: hips hidden behind the front wall, scale s. */
const sisPose = (s: number, extra: Partial<Pose> = {}): Pose => ({ ...basePose, x: 960, y: HOUSE.eave + 120, scale: s, yaw: 0.1, look: 0.2, armL: { a: 40, b: 30 }, armR: { a: 40, b: 30 }, ...extra });

// ---------- S1: wide, the stairwell: « You run. » Pip hobbles up, crutch first; PART 2 ----------
export const S1: React.FC<ShotProps> = ({ t, len }) => {
  const x = kf(t, [[0, 1520], [len, 980]], (u) => u);
  const phase = t * 0.45;
  const pose: Pose = walkPose(x, phase, hipGround, 0.9, { armL: { a: 20, b: 20 }, armR: { a: 30, b: 30 } }, -1);
  const floor = hipGround(x) ;
  return (
    <g transform={camT(kf(t, [[0, 1300], [len, 1000]]), kf(t, [[0, 640], [len, 560]]), 1.15)}>
      <Stairwell t={t + 30} id="p2sw1" />
      <Crutch pose={pose} floor={floor + 4} dx={-30} />
      <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'worried']]) }} rimId="rimL" shadow={0.5} />
      <LegCast pose={pose} leg="legL" />
      <Banister />
      <TitleCard t={t} lines={['WHAT IF YOU COULD GROW AT WILL?', 'PART 2']} accent="2" accentT={24} size={110} y={150} />
    </g>
  );
};

// S2: insert, low: « Crutch first, every stair. » The rubber tip, then the cast, step by step
export const S2: React.FC<ShotProps> = ({ t, len }) => {
  const step = (t % 18) / 18;
  const tipY = kf(step, [[0, 380], [0.3, 520], [1, 520]]);
  const castY = kf(step, [[0, 560], [0.5, 560], [0.8, 430], [1, 430]]);
  return (
    <g>
      <rect x={-100} y={-100} width={2120} height={1280} fill="#2B2432" />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <rect x={-200 + i * 760} y={760 - i * 260} width={900} height={60} fill="#6A4E40" />
          <rect x={-200 + i * 760} y={820 - i * 260} width={900} height={500} fill="#3A2826" />
          <path d={`M ${-200 + i * 760} ${760 - i * 260} L ${700 + i * 760} ${760 - i * 260}`} stroke="#FFB15A" strokeWidth={4} opacity={0.5} />
        </g>
      ))}
      <Glow x={1400} y={200} r={700} o={0.4} />
      {/* the crutch: two aluminium legs to a rubber tip */}
      <path d={`M 1180 -100 L 1140 ${tipY} M 1220 -100 L 1150 ${tipY}`} stroke="#9AA0A8" strokeWidth={22} strokeLinecap="round" />
      <ellipse cx={1146} cy={tipY + 20} rx={34} ry={22} fill="#2A2A30" />
      {/* the cast, the foot in a sock */}
      <g transform={`translate(760 ${castY})`}>
        <rect x={-90} y={-600} width={180} height={560} rx={70} fill="#14121C" />
        <rect x={-80} y={-600} width={160} height={550} rx={64} fill="#F2EEE6" />
        <path d="M -30 -400 l 40 16 l -16 30" stroke="#4A7AA0" strokeWidth={8} fill="none" />
        <path d="M -20 -240 q 26 -26 46 0" stroke="#D9534F" strokeWidth={8} fill="none" />
        <ellipse cx={30} cy={-30} rx={130} ry={50} fill="#2FB7A6" stroke="#14121C" strokeWidth={8} />
      </g>
      <rect x={-100} y={-100} width={2120} height={1280} fill="#07040C" opacity={0.15} />
    </g>
  );
};

// S3: medium: « Her door won't open. » Pip shoulders the door on the landing; gold light round its edges, it bulges
export const S3: React.FC<ShotProps> = ({ t, len }) => {
  const shove = Math.max(0, Math.sin(t / 3)) * 10;
  const bulge = settle(t - 6, 8, 1.6, 10);
  const door = { x: 160, y: 120, w: 170, h: 300 };
  const pose = poseAt(t, [
    { f: 0, p: { x: 380, y: feetAt(SW.top, 0.9), scale: 0.9, yaw: -0.7, facing: -1, look: -1, tilt: -10, armL: { a: 70, b: 30 }, armR: { a: 60, b: 40 } } },
  ]);
  return (
    <g transform={camT(300, 260, 1.7)}>
      <Stairwell t={t + 60} id="p2sw3" />
      <g transform={`translate(${-bulge} 0)`}>
        <rect x={door.x - 8} y={door.y - 8} width={door.w + 16} height={door.h + 8} fill="#1E1824" />
        <rect x={door.x} y={door.y} width={door.w} height={door.h} fill="#6A4A3E" />
        <rect x={door.x + 18} y={door.y + 20} width={door.w - 36} height={110} fill="#5A3E34" />
        <rect x={door.x + 18} y={door.y + 160} width={door.w - 36} height={120} fill="#5A3E34" />
        <circle cx={door.x + door.w - 24} cy={door.y + 160} r={8} fill="#E9C46A" />
        <path d={`M ${door.x} ${door.y} L ${door.x} ${door.y + door.h} M ${door.x + door.w} ${door.y} L ${door.x + door.w} ${door.y + door.h} M ${door.x} ${door.y} L ${door.x + door.w} ${door.y}`} stroke={GOLD} strokeWidth={5} opacity={0.6 + 0.4 * Math.sin(t / 2)} />
      </g>
      <Glow x={door.x + door.w / 2} y={door.y + door.h / 2} r={260} o={0.4} />
      <Hero look={PIP} pose={{ ...pose, x: 380 - shove, ...faceAt(t, [[0, 'oops']]) }} rimId="rimL" shadow={0.5} />
    </g>
  );
};

// S4: low, from the street: « Because her room isn't a room anymore. » The roof bursts, a giant head of bunches rises
export const S4: React.FC<ShotProps> = ({ t, len }) => {
  const t0 = Math.max(4, len - 14);
  const rise = easeOut(clamp((t - t0) / 12));
  const s = 2.6;
  const sis = sisPose(s, { y: HOUSE.eave + 120 + (1 - rise) * 420, look: 0.6, armL: { a: 20, b: 10 }, armR: { a: 20, b: 10 } });
  return (
    <g transform={camT(960, kf(t, [[0, 520], [len, 470]]), kf(t, [[0, 1.3], [len, 1.18]]))}>
      <HouseScene t={t + 10} id="p2h4" sis={{ ...sis, ...faceAt(t, [[0, 'happy']]) }} burst={rise}
        front={Array.from({ length: 14 }).map((_, i) => {
          const tt = t - t0 - (i % 4);
          if (tt < 0) return null;
          const vx = (rnd(31, i) - 0.5) * 30;
          const x = 960 + (rnd(32, i) - 0.5) * 300 + vx * tt;
          const y = HOUSE.apex + 60 - 22 * tt + 1.3 * tt * tt;
          return <rect key={i} x={x} y={y} width={26} height={14} fill="#241A30" stroke="#120C18" strokeWidth={3} transform={`rotate(${tt * 20 * (i % 2 ? 1 : -1)} ${x} ${y})`} />;
        })}
      />
    </g>
  );
};

// S5: wide: « Your little sister is the size of the house. » She leans on the roof, delighted
export const S5: React.FC<ShotProps> = ({ t, len }) => {
  const sis = poseAt(t, [
    { f: 0, p: sisPose(2.6, { armL: { a: 70, b: 40 }, armR: { a: 70, b: 40 } }) },
    { f: 12, p: { armL: { a: 100, b: 30 }, armR: { a: 95, b: 30 }, headTilt: 5 }, ease: easeOut },
  ]);
  return (
    <g transform={camT(960, kf(t, [[0, 520], [len, 540]]), kf(t, [[0, 1.0], [len, 1.06]]))}>
      <HouseScene t={t + 40} id="p2h5" sis={{ ...sis, ...faceAt(t, [[0, 'happy']]) }} />
      <Pigeons x={960} y={180} t={t} rx={420} ry={80} n={5} />
    </g>
  );
};

// S6: close-up: « And she loves it. » The giant face, laughing, bunches swinging
export const S6: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 5.4;
  const head = { x: 960, y: 600 };
  const pose: Pose = { ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: -0.15, look: 0.3, headTilt: Math.sin(t / 4) * 4, sway: Math.sin(t / 3) * 14, armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'happy']]) };
  return (
    <g>
      <g filter="url(#blur16)">
        <g transform="translate(-560 -560) scale(2)">
          <StreetSet t={t + 80} id="p2s6" sunX={1300} sunY={600} />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.2} />
      <Hero look={SIS} pose={pose} rimId="rimR" shadow={0} />
      {t > 6 ? <Sparkle x={1400} y={260} t={t - 6} s={1.4} /> : null}
    </g>
  );
};

// S7: medium: « She laughs, and every window on the street rattles. » A house front across the road, its windows shaking
export const S7: React.FC<ShotProps> = ({ t, len }) => {
  const r = clamp((t - 6) / 4) * (1 - clamp((t - len + 6) / 6));
  return (
    <g transform={`translate(${Math.sin(t * 2.7) * 6 * r} ${Math.cos(t * 3.1) * 4 * r})`}>
      <StreetSet t={t + 120} id="p2s7" sunX={300} sunY={560} />
      <rect x={160} y={240} width={1600} height={1000} fill="#2E2240" />
      <path d="M 160 240 L 1760 240" stroke="#FFB15A" strokeWidth={5} opacity={0.5} />
      {Array.from({ length: 4 }).map((_, c) =>
        Array.from({ length: 3 }).map((__, rr) => {
          const i = c * 3 + rr;
          const dx = Math.sin(t * 3.7 + i * 1.3) * 7 * r;
          const dy = Math.cos(t * 4.1 + i) * 4 * r;
          const x = 260 + c * 380;
          const y = 320 + rr * 260;
          return (
            <g key={i} transform={`translate(${dx} ${dy})`}>
              <rect x={x} y={y} width={240} height={190} fill="#140E1C" />
              <rect x={x + 12} y={y + 12} width={216} height={166} fill={rnd(9, i) > 0.4 ? '#FFC27A' : '#3A3050'} opacity={0.85} />
              <path d={`M ${x + 120} ${y + 12} L ${x + 120} ${y + 178}`} stroke="#140E1C" strokeWidth={8} />
              {r > 0.5 && rnd(10, i + Math.floor(t / 3)) > 0.7 ? <path d={`M ${x + 30} ${y + 40} l 30 -20`} stroke="#FFFFFF" strokeWidth={4} opacity={0.8} /> : null}
            </g>
          );
        }),
      )}
      <Foreground blur={10}>
        <rect x={-100} y={900} width={2200} height={300} fill="#120C18" />
      </Foreground>
    </g>
  );
};

// S8: close-up: « Here's what you didn't know: the word works for anyone who hears it. » Pip below, looking up; gold rings
export const S8: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 3.2;
  const head = { x: 1200, y: 620 };
  const pose: Pose = { ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: -0.25, look: kf(t, [[0, -0.2], [len * 0.5, -0.8]]), headTilt: -8, armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'shock'], [Math.round(len * 0.55), 'worried']]) };
  return (
    <g>
      <g filter="url(#blur16)">
        <g transform="translate(-700 -300) scale(1.8)">
          <HouseScene t={t + 60} id="p2h8" sis={sisPose(2.6, { armL: { a: 100, b: 30 }, armR: { a: 95, b: 30 }, expr: 'happy' })} />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.3} />
      {[0, 1, 2].map((i) => {
        const tt = (t + i * 12) % 36;
        return <circle key={i} cx={480} cy={160} r={60 + tt * 26} fill="none" stroke={GOLD} strokeWidth={6} opacity={0.6 * (1 - tt / 36)} />;
      })}
      <Hero look={PIP} pose={pose} rimId="rimL" shadow={0} />
    </g>
  );
};

// S9: wide: « She waves at the whole street. » Tiny Mo and Mum on the pavement wave back
export const S9: React.FC<ShotProps> = ({ t, len }) => {
  const w = Math.sin(t / 3) * 16;
  return (
    <g transform={camT(960, 560, kf(t, [[0, 0.98], [len, 1.04]]))}>
      <HouseScene t={t + 90} id="p2h9" sis={{ ...sisPose(2.6, { armR: { a: 150 + w, b: 20 }, armL: { a: 60, b: 30 } }), ...faceAt(t, [[0, 'happy']]) }}
        front={
          <g>
            <Hero look={MO} pose={{ ...basePose, x: 380, y: feetAt(1060, 0.42), scale: 0.42, yaw: 0.3, look: 1, armR: { a: 150 - w, b: 20 } }} rimId="rimR" shadow={1} />
            <Hero look={MOM} pose={{ ...basePose, x: 1540, y: feetAt(1060, 0.44), scale: 0.44, yaw: -0.4, look: -1, armL: { a: 30, b: 70 }, armR: { a: 30, b: 70 }, expr: 'shock' }} rimId="rimL" shadow={1} />
          </g>
        }
      />
    </g>
  );
};

// S10: medium: « Mum faints. Twice. » On the doorstep: she goes over backwards, gets up, goes over again
export const S10: React.FC<ShotProps> = ({ t, len }) => {
  const second = Math.max(14, len - 16);
  const t0first = 4;
  const fall = (t0: number) => easeIn(clamp((t - t0) / 6));
  const up = easeOut(clamp((t - (t0first + 8)) / 6));
  const spin = t < second ? -84 * fall(t0first) * (1 - up) : -84 * fall(second);
  const pose: Pose = { ...basePose, x: 960, y: feetAt(900, 1.2) + Math.abs(spin) * 2.2, scale: 1.2, yaw: 0.2, look: 0.6, spin, armL: { a: 60 + Math.abs(spin) * 0.6, b: 20 }, armR: { a: 60 + Math.abs(spin) * 0.6, b: 20 }, ...faceAt(t, [[0, 'shock'], [t0first + 5, 'dizzy'], [t0first + 14, 'shock'], [second + 4, 'dizzy']]) };
  return (
    <g transform={camT(960, 600, 1.35)}>
      <StreetSet t={t + 140} id="p2s10" sunX={1500} sunY={600} />
      <rect x={560} y={300} width={800} height={900} fill="#3A2C48" />
      <rect x={830} y={380} width={260} height={540} fill="#FFD9A0" opacity={0.9} />
      <Glow x={960} y={600} r={520} o={0.5} />
      <rect x={520} y={900} width={880} height={40} fill="#5A4A5A" />
      <Hero look={MOM} pose={pose} rimId="rimL" shadow={0.6} />
      {spin < -60 ? <DizzyStars x={960 - 200} y={880} t={t} rx={90} ry={30} /> : null}
    </g>
  );
};

// S11: insert: « She picks up the cat, very gently. » The cat on her giant palm, rising past the windows
export const S11: React.FC<ShotProps> = ({ t, len }) => {
  const lift = kf(t, [[0, 260], [len, -40]], easeInOut);
  const palm = { x: 980, y: 700 + lift };
  return (
    <g>
      <g filter="url(#blur10)">
        <g transform="translate(-300 -200) scale(1.4)">
          <StreetSet t={t + 160} id="p2s11" sunX={1300} sunY={620} />
        </g>
      </g>
      <g filter="url(#rimR)">
        <path d={`M ${palm.x + 900} 1500 Q ${palm.x + 500} ${palm.y + 400} ${palm.x + 220} ${palm.y + 110}`} stroke={SIS.line} strokeWidth={280} fill="none" strokeLinecap="round" />
        <path d={`M ${palm.x + 900} 1500 Q ${palm.x + 500} ${palm.y + 400} ${palm.x + 220} ${palm.y + 110}`} stroke={SIS.limb} strokeWidth={250} fill="none" strokeLinecap="round" />
        <ellipse cx={palm.x} cy={palm.y + 40} rx={300} ry={100} fill={SIS.hand} stroke={SIS.line} strokeWidth={12} />
        <ellipse cx={palm.x - 250} cy={palm.y - 30} rx={56} ry={100} fill={SIS.hand} stroke={SIS.line} strokeWidth={12} transform={`rotate(-25 ${palm.x - 250} ${palm.y - 30})`} />
      </g>
      <g transform={`translate(${palm.x + 40} ${palm.y + 20}) scale(2)`}>
        <Cat x={0} y={0} mood={t > len * 0.4 ? 'alert' : 'peek'} f={t} />
      </g>
    </g>
  );
};

// S12: wide: « Then she sways. » Her smile goes, she rocks, stars round her head
export const S12: React.FC<ShotProps> = ({ t, len }) => {
  const sway = Math.sin(t / 5) * 10 * clamp(t / 12);
  return (
    <g transform={camT(960, 520, kf(t, [[0, 1.0], [len, 1.08]]))}>
      <HouseScene t={t + 200} id="p2h12" red={0.2 * clamp(t / len)} sis={{ ...sisPose(2.6, { tilt: sway, headTilt: sway * 0.8, armL: { a: 60, b: 40 }, armR: { a: 60, b: 40 } }), ...faceAt(t, [[0, 'neutral'], [8, 'dizzy']]) }}
        extra={t > 8 ? <DizzyStars x={960 + sway * 8} y={HOUSE.eave + 120 - 176 * 2.6} t={t} rx={260} ry={70} /> : null} />
    </g>
  );
};

// ---------- the turn: the schematic ----------
/** A figure in outline with its heart and its brain marked, and the height between them. */
const HeartBrain: React.FC<{ x: number; y: number; h: number; t: number; color?: string; label?: string }> = ({ x, y, h, t, color = SCH.line, label }) => {
  const k = h / 400;
  const heart = { x: x + 8 * k, y: y - 250 * k };
  const brain = { x, y: y - 340 * k };
  return (
    <g>
      <DrawOn d={`M ${x - 30 * k} ${y} L ${x - 12 * k} ${y - 140 * k} L ${x + 12 * k} ${y - 140 * k} L ${x + 30 * k} ${y} M ${x - 40 * k} ${y - 140 * k} L ${x - 44 * k} ${y - 252 * k} Q ${x} ${y - 262 * k} ${x + 44 * k} ${y - 252 * k} L ${x + 40 * k} ${y - 140 * k} Z`} t={t} dur={10} color={color} width={Math.max(3, 4 * Math.min(1, k * 2))} />
      {t > 3 ? <circle cx={x} cy={y - 330 * k} r={62 * k} fill="none" stroke={color} strokeWidth={Math.max(3, 4 * Math.min(1, k * 2))} opacity={clamp((t - 3) / 5)} /> : null}
      {t > 8 ? <circle cx={heart.x} cy={heart.y} r={Math.max(7, 16 * k)} fill={UI.bad} opacity={0.6 + 0.4 * Math.abs(Math.sin(t / 4))} /> : null}
      {t > 10 ? <circle cx={brain.x} cy={brain.y} r={Math.max(7, 20 * k)} fill="#9FC0FF" opacity={0.85} /> : null}
      {t > 12 && label ? (
        <g>
          <path d={`M ${x + 90 * k + 20} ${heart.y} L ${x + 90 * k + 20} ${brain.y}`} stroke={SCH.live} strokeWidth={5} />
          <path d={`M ${x + 90 * k + 8} ${heart.y} L ${x + 90 * k + 32} ${heart.y} M ${x + 90 * k + 8} ${brain.y} L ${x + 90 * k + 32} ${brain.y}`} stroke={SCH.live} strokeWidth={5} />
          <SchLabel x={x + 90 * k + 50} y={(heart.y + brain.y) / 2 + 12} t={t - 12} text={label} size={34} color={SCH.live} anchor="start" />
        </g>
      ) : null}
    </g>
  );
};

// S13: schematic: « Blood is heavy. At ten times her height, her heart has to push it ten times higher. »
export const S13: React.FC<ShotProps> = ({ t, len }) => (
  <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
    <Schematic t={t} id="p2sch13" />
    <DrawOn d="M 160 940 L 1500 940" t={t} dur={8} color={SCH.dim} width={3} />
    <HeartBrain x={300} y={940} h={80} t={t - 2} />
    <SchLabel x={300} y={1000} t={t - 4} text="×1" size={34} color={SCH.dim} />
    <SchLabel x={420} y={830} t={t - 10} text="0.3 m" size={30} color={SCH.dim} anchor="start" />
    <HeartBrain x={900} y={940} h={800} t={t - Math.round(len * 0.35)} color={GOLD} label="3 m" />
    <SchLabel x={900} y={1000} t={t - Math.round(len * 0.35)} text="×10" size={40} color={GOLD} />
    <SchLabel x={1500} y={180} t={t - 6} text="BLOOD IS HEAVY" size={50} color={SCH.line} />
    <SchLabel x={1500} y={240} t={t - 10} text="1,060 kg per cubic metre" size={28} color={SCH.dim} />
  </g>
);

// S14: schematic: « That takes about three times the pressure her heart can make. » Two bars, one three times the other
export const S14: React.FC<ShotProps> = ({ t, len }) => {
  const p = easeOut(clamp((t - 8) / Math.max(16, len - 24)));
  const base = 880;
  const unit = 190;
  const bar = (x: number, v: number, color: string, t0: number) => {
    const h = unit * v * easeOut(clamp((t - t0) / 14));
    return <rect x={x - 90} y={base - h} width={180} height={h} rx={10} fill={color} opacity={0.85} stroke={SCH.line} strokeWidth={3} />;
  };
  return (
    <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
      <Schematic t={t + 90} id="p2sch14" />
      <DrawOn d={`M 340 ${base} L 1600 ${base}`} t={t} dur={8} color={SCH.dim} width={3} />
      {bar(640, 1, '#9FC0FF', 4)}
      {bar(1280, 3 * p, SCH.live, 8)}
      <SchLabel x={640} y={base + 60} t={t - 6} text="WHAT HER HEART MAKES" size={30} color={SCH.dim} />
      <SchLabel x={640} y={base + 100} t={t - 8} text="~80 mmHg" size={30} color={SCH.line} />
      <SchLabel x={1280} y={base + 60} t={t - 10} text="WHAT 3 m OF BLOOD NEEDS" size={30} color={SCH.dim} />
      <SchLabel x={1280} y={base + 100} t={t - 12} text="~235 mmHg" size={30} color={SCH.line} />
      <SchLabel x={1280} y={base - unit * 3 - 40} t={t - Math.round(len * 0.6)} text="×3" size={80} color={SCH.live} />
    </g>
  );
};

// S15: schematic: « And without blood, a brain switches off in about ten seconds. » The countdown
export const S15: React.FC<ShotProps> = ({ t, len }) => {
  const p = clamp((t - 6) / Math.max(20, len - 10));
  const s = Math.ceil(10 * (1 - p));
  return (
    <g transform={`translate(960 540) scale(${kf(t, [[0, 1], [len, 1.04]])}) translate(-960 -540)`}>
      <Schematic t={t + 180} id="p2sch15" />
      <g transform="translate(560 540) scale(2.2)">
        <path d="M -60 -40 Q -70 -110 0 -112 Q 70 -110 60 -40 Q 70 10 30 30 L -30 30 Q -70 10 -60 -40 Z" fill="none" stroke={SCH.line} strokeWidth={3} />
        <path d="M -40 -60 q 20 -20 40 0 q 20 20 40 0 M -40 -20 q 20 -20 40 0 q 20 20 40 0" stroke="#9FC0FF" strokeWidth={3} fill="none" opacity={1 - p * 0.9} />
      </g>
      <SchLabel x={560} y={900} t={t - 4} text="NO BLOOD TO THE BRAIN" size={32} color={SCH.dim} />
      <Dial x={1320} y={500} r={230} p={1 - p} readout={`00:${String(s).padStart(2, '0')}`} size={96} />
      <SchLabel x={1320} y={840} t={t - 8} text="LIGHTS OUT IN ~10 s" size={36} color={UI.bad} />
    </g>
  );
};

// S16: extreme close-up: « That's real. » Her eyes going, red rim
export const S16: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 6.2;
  const head = { x: 960, y: 640 };
  const pose: Pose = { ...basePose, x: head.x + Math.sin(t / 4) * 20, y: head.y - HEAD.y * sc, scale: sc, yaw: 0.05, look: Math.sin(t / 3) * 0.5, headTilt: Math.sin(t / 5) * 6, armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'dizzy'], [Math.round(len * 0.5), 'tired']]) };
  return (
    <g>
      <g filter="url(#blur16)">
        <g transform="translate(-560 -640) scale(2)">
          <StreetSet t={t + 240} id="p2s16" red={0.6} sunX={1300} sunY={600} />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.25} />
      <Hero look={SIS} pose={pose} rimId="rimRed" shadow={0} />
    </g>
  );
};

// ---------- the countdown and the catch ----------
/** Pip on the pavement in front of our house, with his cast and crutch, at scale s (feet on y 1060). */
const pipStreet = (s: number, extra: Partial<Pose> = {}): Pose => ({ ...basePose, x: 1450, y: feetAt(1060, s), scale: s, yaw: -0.5, facing: -1, look: -0.8, armL: { a: 14, b: -8 }, armR: { a: 24, b: 10 }, ...extra });

// S17: wide: « Ten seconds. » The dial over the street; Pip looks up at her, small
export const S17: React.FC<ShotProps> = ({ t, len }) => {
  const sway = Math.sin(t / 5) * 12;
  const p = clamp(t / (len * 3));
  const pose = pipStreet(0.55, { headTilt: -6 });
  return (
    <g transform={camT(1020, 560, 1.0)}>
      <HouseScene t={t + 260} id="p2h17" red={0.3} sis={{ ...sisPose(2.6, { tilt: sway, headTilt: sway, armL: { a: 40, b: 50 }, armR: { a: 40, b: 50 } }), ...faceAt(t, [[0, 'tired']]) }}
        front={
          <g>
            <Crutch pose={pose} floor={1060} />
            <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'shock']]) }} rimId="rimL" shadow={1} />
            <LegCast pose={pose} leg="legL" />
          </g>
        }
      />
      <Dial x={1640} y={220} r={120} p={1 - p} readout="00:10" size={60} />
    </g>
  );
};

// S18: close-up: « There's only one way to catch her. » Pip makes up his mind: the gold comes into his eyes
export const S18: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 3.4;
  const head = { x: 900, y: 620 };
  const pose: Pose = { ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: 0.3, look: kf(t, [[0, 0.8], [len * 0.5, 0.1]]), headTilt: kf(t, [[0, -8], [len, 0]]), armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, glint: clamp((t - len + 14) / 6), glintColor: GOLD, ...faceAt(t, [[0, 'worried'], [Math.round(len * 0.5), 'neutral']]) };
  return (
    <g>
      <g filter="url(#blur16)">
        <g transform="translate(-400 -420) scale(1.8)">
          <HouseScene t={t + 280} id="p2h18" red={0.35} sis={sisPose(2.6, { tilt: 8, expr: 'tired' })} />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.3} />
      <Hero look={PIP} pose={pose} rimId="rimR" shadow={0} />
      <Dial x={1700} y={180} r={90} p={0.9} readout="00:09" size={44} />
    </g>
  );
};

// S19: wide: « You say the word. » Pip grows in the street, cast and all (the power's look)
export const S19: React.FC<ShotProps> = ({ t, len }) => {
  const t0 = Math.max(6, len - 12);
  const g = growth(t, t0, 0.55, 2.0, 7);
  const pose = pipStreet(g.scale, { squash: g.squash, glint: g.glint, glintColor: GOLD, armL: { a: 40, b: 30 }, armR: { a: 40, b: 30 } });
  return (
    <g transform={camT(1100, kf(t, [[0, 600], [len, 520]]), kf(t, [[0, 1.08], [len, 0.98]]))}>
      <HouseScene t={t + 300} id="p2h19" red={0.35} sis={{ ...sisPose(2.6, { tilt: 10, headTilt: 8 }), ...faceAt(t, [[0, 'tired']]) }}
        front={
          <g>
            <GrowFx x={1450} y={1060} t={t - t0} s={1.6} />
            <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'neutral'], [t0 + 4, 'oops']]) }} rimId="rimL" shadow={1} />
            <LegCast pose={pose} leg="legL" />
          </g>
        }
      />
    </g>
  );
};

// S20: insert: « Your leg isn't healed. » The cast, huge now, cracking along its length
export const S20: React.FC<ShotProps> = ({ t, len }) => {
  const c = clamp((t - 6) / 10);
  return (
    <g transform={`translate(${t > 6 && t < 12 ? Math.sin(t * 3) * 8 : 0} 0)`}>
      <StreetSet t={t + 320} id="p2s20" red={0.4} sunX={300} sunY={500} />
      <rect x={-100} y={-100} width={2120} height={1280} fill="#07040C" opacity={0.35} />
      <g transform="rotate(-12 960 540)">
        <rect x={720} y={-200} width={480} height={1500} rx={200} fill="#14121C" />
        <rect x={744} y={-200} width={432} height={1500} rx={190} fill="#F2EEE6" />
        <path d="M 820 300 l 60 30 l -24 46" stroke="#4A7AA0" strokeWidth={14} fill="none" />
        <DrawOn d="M 960 -100 L 990 120 L 930 260 L 1010 420 L 950 600 L 1030 820 L 980 1100" t={t - 6} dur={10} color="#14121C" width={12} />
        <DrawOn d="M 930 260 L 860 330 M 1010 420 L 1100 470 M 950 600 L 860 660" t={t - 10} dur={8} color="#14121C" width={8} />
        {c > 0 ? Array.from({ length: 10 }).map((_, i) => <circle key={i} cx={960 + (rnd(5, i) - 0.5) * 200} cy={200 + rnd(6, i) * 600 + (t - 6) * 6} r={5 + rnd(7, i) * 8} fill="#E6E0D4" opacity={0.8 * (1 - c * 0.5)} />) : null}
      </g>
      {t > 6 && t < 9 ? <rect x={0} y={0} width={1920} height={1080} fill={UI.bad} opacity={0.25} /> : null}
    </g>
  );
};

// S21: wide: « You do it anyway. » One limping giant step toward the house
export const S21: React.FC<ShotProps> = ({ t, len }) => {
  const k = easeInOut(clamp(t / len));
  const pose = poseAt(t, [
    { f: 0, p: { ...pipStreet(2.0), x: 1450, yaw: -0.85, look: -1, tilt: -6, legL: { a: -30, b: -40 }, legR: { a: 30, b: 0 }, armL: { a: 50, b: 30 }, armR: { a: 70, b: 30 } } },
    { f: Math.round(len * 0.6), p: { x: 1350, legL: { a: 10, b: 0 }, legR: { a: -10, b: -20 }, tilt: -12 }, ease: easeInOut },
    { f: len, p: { x: 1330, tilt: -8 } },
  ]);
  return (
    <g transform={camT(kf(t, [[0, 1150], [len, 1080]]), 540, 1.02)}>
      <HouseScene t={t + 340} id="p2h21" red={0.4} sis={{ ...sisPose(2.6, { tilt: 14 + 6 * k, headTilt: 10 }), ...faceAt(t, [[0, 'tired']]) }}
        front={
          <g>
            <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'oops'], [Math.round(len * 0.6), 'worried']]) }} rimId="rimL" shadow={1} />
            <LegCast pose={pose} leg="legL" />
          </g>
        }
      />
    </g>
  );
};

// S22: wide: « Nine. Eight. » She topples out of the roof toward the street
export const S22: React.FC<ShotProps> = ({ t, len }) => {
  const k = easeIn(clamp(t / len));
  const sis = sisPose(2.6, { tilt: 14 + 50 * k, headTilt: 12, armL: { a: 60 + 60 * k, b: 20 }, armR: { a: 60 + 60 * k, b: 20 }, expr: 'tired', blink: 1 });
  const read = t < len * 0.5 ? '00:09' : '00:08';
  return (
    <g transform={camT(960, 520, kf(t, [[0, 1.0], [len, 1.06]]))}>
      <HouseScene t={t + 360} id="p2h22" red={0.45} sis={sis} />
      <Dial x={1700} y={180} r={100} p={t < len * 0.5 ? 0.9 : 0.8} readout={read} size={50} />
    </g>
  );
};

// S23: wide: « You catch her. » Pip, giant, takes her in his arms in front of the house; the gold flares
export const S23: React.FC<ShotProps> = ({ t, len }) => {
  const catchT = 6;
  const k = easeOut(clamp((t - catchT) / 6));
  const pip = poseAt(t, [
    { f: 0, p: { ...pipStreet(2.0), x: 1200, yaw: -0.4, look: -0.6, armL: { a: 80, b: 40 }, armR: { a: 80, b: 40 } } },
    { f: catchT, p: { armL: { a: 55, b: 45 }, armR: { a: 55, b: 45 }, squash: 0.06 }, ease: easeOut },
    { f: catchT + 6, p: { squash: 0, headTilt: 8 } },
  ]);
  const j = joints(pip);
  const hands = toWorld(pip, j.armR.end);
  const sis: Pose = { ...basePose, x: pip.x + 40 + (1 - k) * -160, y: pip.y - 20 - (1 - k) * 260, scale: 1.2, spin: -84 + (1 - k) * 30, yaw: 0.3, armL: { a: 120, b: 30 }, armR: { a: 30, b: 20 }, legL: { a: 20, b: -10 }, legR: { a: 40, b: -20 }, expr: 'tired', blink: 1 };
  return (
    <g transform={camT(1100, 520, kf(t, [[0, 1.0], [len, 1.08]]))}>
      <StreetSet t={t + 380} id="p2s23" red={0.3 * (1 - k)} sunX={1560} sunY={620}
        front={
          <g>
            <OurHouse t={t} burst={1} />
            <Hero look={PIP} pose={{ ...pip, ...faceAt(t, [[0, 'worried'], [catchT + 4, 'happy']]) }} rimId="rimL" shadow={1} />
            <Hero look={SIS} pose={sis} rimId="rimR" shadow={0} />
            <LegCast pose={pip} leg="legL" />
            <FocusRings x={hands.x} y={hands.y - 60} t={(t - catchT) * 1.4} r0={140} color={GOLD} />
            {t > catchT + 4 ? <Sparkle x={hands.x + 200} y={hands.y - 300} t={t - catchT - 4} s={1.6} /> : null}
          </g>
        }
      />
    </g>
  );
};

// S24: wide: « Then you both sit down, and wait. Slowly, the street gets bigger again. » Night; they shrink side by side
export const S24: React.FC<ShotProps> = ({ t, len }) => {
  const k = easeInOut(clamp(t / len));
  const sp = 2.0 - 1.2 * k;
  const ss = 1.4 - 0.85 * k;
  const ground = 1040;
  const sitPose = (x: number, s: number, extra: Partial<Pose> = {}): Pose => ({ ...basePose, x, y: ground - 70 * s, scale: s, yaw: -0.85, facing: -1, look: -0.2, tilt: -6, legL: { a: 82, b: -78 }, legR: { a: 76, b: -60 }, armL: { a: 40, b: -30 }, armR: { a: 30, b: -20 }, ...extra });
  return (
    <g transform={camT(980, kf(t, [[0, 560], [len, 620]]), kf(t, [[0, 1.0], [len, 1.12]]))}>
      <StreetSet t={t + 400} id="p2s24" red={0.4 * (1 - k)} sunX={700} sunY={640 + 300 * k}
        front={
          <g>
            <rect x={-400} y={-400} width={2720} height={1900} fill="#070B22" opacity={0.6 * k} />
            <Stars seed={9} x0={-200} y0={-200} w={2320} h={700} t={t} n={60} o={0.9 * k} />
            <g opacity={k}>
              <Moon x={1500} y={220} r={60} bloom={k} />
            </g>
            <OurHouse t={t} burst={1} />
            <rect x={-400} y={ground} width={2720} height={400} fill="#120C18" />
            <Hero look={PIP} pose={{ ...sitPose(1180, sp), ...faceAt(t, [[0, 'tired']]) }} rimId={k > 0.5 ? 'rimBlue' : 'rimL'} shadow={0} />
            <Hero look={SIS} pose={{ ...sitPose(760, ss, { yaw: 0.85, facing: 1, look: 0.4 }), ...faceAt(t, [[0, 'tired'], [Math.round(len * 0.6), 'happy']]) }} rimId={k > 0.5 ? 'rimBlueL' : 'rimR'} shadow={0} />
            {Array.from({ length: 10 }).map((_, i) => {
              const tt = (t * 0.6 + i * 9) % 30;
              return <circle key={i} cx={760 + rnd(81, i) * 480} cy={900 - tt * 7} r={3} fill={GOLD} opacity={0.6 * (1 - tt / 30) * clamp(t / 10)} />;
            })}
          </g>
        }
      />
    </g>
  );
};

// ---------- someone powerful is watching ----------
// S25: medium: « Across the street, the man in the suit isn't calling for help. » He holds his phone up, filming
export const S25: React.FC<ShotProps> = ({ t, len }) => {
  const pose = poseAt(t, [{ f: 0, p: { x: 900, y: feetAt(1000, 1.3), scale: 1.3, yaw: 0.5, look: 0.9, armL: { a: 14, b: -8 }, armR: { a: 70, b: 90 } } }]);
  const j = joints(pose);
  const hand = toWorld(pose, j.armR.end);
  return (
    <g transform={camT(980, 560, 1.5)}>
      <StreetSet t={t + 420} id="p2s25" sunX={1600} sunY={600} />
      <rect x={-400} y={-400} width={2720} height={1900} fill="#070B22" opacity={0.45} />
      <Stars seed={4} x0={-200} y0={-200} w={2320} h={500} t={t} n={40} o={0.6} />
      <Glow x={1300} y={500} r={600} o={0.25} kind="cool" />
      <Hero look={SUIT} pose={{ ...pose, ...faceAt(t, [[0, 'neutral'], [Math.round(len * 0.5), 'smug']]) }} rimId="rimBlue" shadow={0.6} />
      <g transform={`translate(${hand.x + 10} ${hand.y - 40}) rotate(-8)`}>
        <rect x={-30} y={-54} width={60} height={108} rx={10} fill="#16161C" stroke="#3A3A44" strokeWidth={4} />
        <rect x={-24} y={-46} width={48} height={92} rx={6} fill="#2A3A5A" />
        <circle cx={14} cy={-36} r={5} fill={UI.bad} opacity={Math.floor(t / 8) % 2 ? 1 : 0.3} />
        <Glow x={0} y={0} r={90} o={0.4} kind="cool" />
      </g>
    </g>
  );
};

// S26: insert: « He's filming. Everything. » His phone screen: the two giants on the street, REC
export const S26: React.FC<ShotProps> = ({ t, len }) => (
  <g transform={`translate(960 540) scale(${kf(t, [[0, 1.0], [len, 1.12]])}) translate(-960 -540)`}>
    <rect x={-100} y={-100} width={2120} height={1280} fill="#07060C" />
    <g filter="url(#blur10)">
      <rect x={-100} y={700} width={2120} height={500} fill="#141022" />
    </g>
    <rect x={560} y={60} width={800} height={960} rx={60} fill="#16161C" stroke="#3A3A44" strokeWidth={10} />
    <defs>
      <clipPath id="p2phone">
        <rect x={600} y={110} width={720} height={860} rx={30} />
      </clipPath>
    </defs>
    <g clipPath="url(#p2phone)">
      <g transform="translate(300 214) scale(0.6)">
        <StreetSet t={t + 440} id="p2s26" red={0.3} sunX={1560} sunY={620} front={<g><OurHouse t={t} burst={1} /><Hero look={PIP} pose={{ ...pipStreet(2.0), x: 1250, expr: 'oops' }} rimId="rimL" shadow={0} /><Hero look={SIS} pose={sisPose(2.6, { tilt: 30, expr: 'tired' })} rimId="rimR" shadow={0} /></g>} />
      </g>
      <rect x={600} y={110} width={720} height={860} fill="#0A1A3A" opacity={0.15} />
      <circle cx={660} cy={170} r={14} fill={UI.bad} opacity={Math.floor(t / 8) % 2 ? 1 : 0.3} />
      <text x={690} y={182} fontFamily={FONT.ui} fontSize={34} fill={UI.text}>REC</text>
      <text x={1290} y={182} textAnchor="end" fontFamily={FONT.ui} fontSize={30} fill={UI.text}>{`00:0${Math.min(9, 4 + Math.floor(t / 30))}:${String(10 + Math.floor(t % 30)).padStart(2, '0')}`}</text>
      <rect x={760} y={420} width={400} height={300} fill="none" stroke={UI.text} strokeWidth={3} strokeDasharray="30 330" opacity={0.7} />
    </g>
  </g>
);

// ---------- the next morning ----------
const BED = bedSit(0.2);

// S27: wide, the bedroom: « The next morning, there's a card on your pillow. » Pip sits up in bed; a white card
export const S27: React.FC<ShotProps> = ({ t, len }) => {
  const pose = poseAt(t, [
    { f: 0, p: { x: BED.x, y: BED.y, scale: BED.scale, yaw: 0.45, look: 0.6, legL: { a: 80, b: 0 }, legR: { a: 80, b: 0 }, armL: { a: 20, b: 20 }, armR: { a: 30, b: 30 }, headTilt: 6 } },
    { f: Math.round(len * 0.5), p: { look: -0.6, headTilt: 12, yaw: 0.1 } },
  ]);
  const card = { x: BED.x - 90, y: BED.y - 60 };
  return (
    <g transform={camT(kf(t, [[0, 820], [len, 760]]), 560, kf(t, [[0, 1.3], [len, 1.45]]))}>
      <Bedroom t={t + 460} id="p2b27" duvet={false} lamp={1} />
      <Hero look={PIP} pose={{ ...pose, ...faceAt(t, [[0, 'tired'], [Math.round(len * 0.5), 'neutral']]) }} rimId="rimBlueL" shadow={0} />
      <BedDuvet knees={1} />
      <g transform={`translate(${card.x} ${card.y}) rotate(-12)`}>
        <rect x={-46} y={-30} width={92} height={60} rx={4} fill="#000" opacity={0.3} transform="translate(4 6)" />
        <rect x={-46} y={-30} width={92} height={60} rx={4} fill="#F6F1E6" />
        <Glow x={0} y={0} r={90} o={0.35} />
      </g>
    </g>
  );
};

// S28: insert, top-down: « One word on it. » The card in his mitten; one word, too blurred to read
export const S28: React.FC<ShotProps> = ({ t, len }) => (
  <g transform={`translate(960 540) rotate(${-3 + t * 0.04}) scale(${kf(t, [[0, 1.0], [len, 1.08]])}) translate(-960 -540)`}>
    <rect x={-200} y={-200} width={2320} height={1480} fill="#4E5E92" />
    {[0.22, 0.48, 0.74].map((k, i) => (
      <path key={i} d={`M -200 ${1080 * k} L 2120 ${1080 * k + 80}`} stroke="#43527F" strokeWidth={10} />
    ))}
    <Glow x={1300} y={300} r={800} o={0.35} />
    <g transform="translate(960 540) rotate(-6)">
      <rect x={-470} y={-290} width={940} height={600} rx={18} fill="#000" opacity={0.35} transform="translate(16 22)" />
      <rect x={-470} y={-290} width={940} height={600} rx={18} fill="#F6F1E6" />
      <g filter="url(#blur10)">
        <text x={0} y={60} textAnchor="middle" fontFamily={FONT.hand} fontWeight={700} fontSize={230} fill="#2A2232">????</text>
      </g>
      <path d="M -400 220 L 400 220" stroke="#C9BCA6" strokeWidth={4} />
    </g>
    <g filter="url(#rimR)">
      <path d="M 1900 1400 Q 1650 1100 1440 900" stroke={PIP.line} strokeWidth={190} fill="none" strokeLinecap="round" />
      <path d="M 1900 1400 Q 1650 1100 1440 900" stroke={PIP.limb} strokeWidth={164} fill="none" strokeLinecap="round" />
      <ellipse cx={1400} cy={860} rx={110} ry={80} fill={PIP.hand} stroke={PIP.line} strokeWidth={10} />
      <ellipse cx={1310} cy={790} rx={44} ry={70} fill={PIP.hand} stroke={PIP.line} strokeWidth={10} transform="rotate(35 1310 790)" />
    </g>
  </g>
);

// S29: close-up: « And it isn't grow. » Pip in bed, wide awake now
export const S29: React.FC<ShotProps> = ({ t, len }) => {
  const sc = 3.2;
  const head = { x: 1180, y: 620 };
  const pose: Pose = { ...basePose, x: head.x, y: head.y - HEAD.y * sc, scale: sc, yaw: -0.2, look: kf(t, [[0, 0.2], [len * 0.4, -0.6]]), headTilt: kf(t, [[0, 0], [len, -6]]), armL: { a: 14, b: -6 }, armR: { a: 14, b: -6 }, ...faceAt(t, [[0, 'neutral'], [Math.round(len * 0.45), 'shock']]) };
  return (
    <g>
      <g filter="url(#blur16)">
        <g transform="translate(-800 -480) scale(1.9)">
          <Bedroom t={t + 480} id="p2b29" lamp={1} />
        </g>
      </g>
      <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.25} />
      <Hero look={PIP} pose={pose} rimId="rimBlue" shadow={0} />
      {t > len * 0.45 ? <FocusRings x={head.x} y={head.y - 40} t={(t - len * 0.45) * 1.4} r0={150} color="#FFE7B3" /> : null}
    </g>
  );
};

// S30: the end card: PART 2, WHAT DO YOU THINK IT SAYS?
export const S30: React.FC<ShotProps> = ({ t, len }) => (
  <g>
    <g opacity={0.35}>
      <S28 t={t + 40} len={len} f={0} />
    </g>
    <rect x={0} y={0} width={1920} height={1080} fill="#07040C" opacity={0.55} />
    <TitleCard t={t} lines={['PART 2', 'WHAT DO YOU THINK IT SAYS?']} accent="SAYS" accentT={22} size={100} y={460} />
  </g>
);

export const _shared = [MO, LAMP, CountUp, Arrow, SW, Foreground];
