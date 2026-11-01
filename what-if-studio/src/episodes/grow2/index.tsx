import React from 'react';
import { defineEpisode, Timeline, LookDef, clamp, easeOut, FONT, UI } from '../../engine';
import timeline from './timeline.json';
import { VERTICAL } from './vertical';
import { S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16, S17, S18, S19, S20, S21, S22, S23, S24, S25, S26, S27, S28, S29, S30 } from './shots';
import { GOLD } from '../grandir/shots';

// The power's look, GROW: the picture warms and rumbles a touch while Pip grows, a GROW chip blinks in the corner and a
// height ruler on the right climbs to his new size. Each growth reads its own sizes: the kitchen, the stairs, the rooftop
// in three steps (Grow, Again, Again) up to ten times his height, then the study. Every growth lands a set number of
// frames before the end of its segment (the shots are end-anchored), so the ruler follows the same rule.

const TL = timeline as Timeline;
const GROW = TL.segments.filter((s) => s.look === 'grow');
const SIZES: [number, number, number][] = [
  [1, 3.6, 12], // S19, the street: from, to, how many frames before the segment's end the growth starts
];
/** The size the ruler shows at a global frame: each growth eases in over 8 frames from its own start in the shot. */
const sizeAt = (f: number) => {
  const i = GROW.findIndex((s) => f >= s.a && f < s.b);
  if (i < 0) return 1;
  const [a, b, t0] = SIZES[Math.min(i, SIZES.length - 1)];
  return a + (b - a) * easeOut(clamp((f - (GROW[i].b - t0)) / 6));
};
const fmt = (v: number) => `×${v < 9.95 ? v.toFixed(1) : Math.round(v)}`;

const GrowOverlay: React.FC<{ f: number; lv: number }> = ({ f }) => {
  const v = sizeAt(f);
  const blink = Math.floor(f / 5) % 2 ? 1 : 0.55;
  const y0 = 900;
  const y1 = 180;
  const k = Math.log(v) / Math.log(10); // 1 at the bottom, 10 at the top
  const my = y0 - (y0 - y1) * k;
  return (
    <g>
      {/* the chip: two chevrons pointing up and the word */}
      <g transform="translate(96 112)">
        <rect x={-30} y={-46} width={250} height={92} rx={46} fill={UI.pill} opacity={0.55} />
        <g opacity={blink} fill="none" stroke={GOLD} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round">
          <path d="M 4 4 L 24 -16 L 44 4" />
          <path d="M 4 24 L 24 4 L 44 24" />
        </g>
        <text x={74} y={16} fontFamily={FONT.ui} fontSize={44} fill={UI.text} letterSpacing={6}>
          GROW
        </text>
      </g>
      {/* the height ruler on the right: ticks, a gold bar up to his size, the readout */}
      <g transform="translate(1800 0)">
        <rect x={-14} y={y1 - 30} width={28} height={y0 - y1 + 60} rx={14} fill={UI.pill} opacity={0.5} />
        {Array.from({ length: 10 }).map((_, i) => {
          const ty = y0 - (y0 - y1) * (Math.log(i + 1) / Math.log(10));
          return <path key={i} d={`M -24 ${ty} L ${i === 0 || i === 9 ? 24 : 10} ${ty}`} stroke={UI.text} strokeWidth={3} opacity={0.7} />;
        })}
        <rect x={-6} y={my} width={12} height={y0 - my} rx={6} fill={GOLD} style={{ filter: `drop-shadow(0 0 10px ${GOLD})` }} />
        <g transform={`translate(-40 ${my})`}>
          <rect x={-150} y={-36} width={150} height={64} rx={32} fill={UI.pill} opacity={0.75} />
          <text x={-75} y={10} textAnchor="middle" fontFamily={FONT.ui} fontSize={38} fill={GOLD}>
            {fmt(v)}
          </text>
        </g>
      </g>
    </g>
  );
};

const grow: LookDef = {
  grade: (lv) => `sepia(${0.16 * lv}) saturate(${1 + 0.18 * lv}) brightness(${1 + 0.05 * lv})`,
  jitter: 2.5,
  Overlay: GrowOverlay,
};

export const grow2Ep = defineEpisode('Grow2', {
  timeline: TL,
  shots: { S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16, S17, S18, S19, S20, S21, S22, S23, S24, S25, S26, S27, S28, S29, S30 },
  looks: { grow },
  vertical: VERTICAL,
});
