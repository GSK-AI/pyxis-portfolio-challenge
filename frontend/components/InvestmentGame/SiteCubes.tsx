"use client";

import { FlaskConical, Hammer } from "lucide-react";

// Fixed footprint: the grid always shows this many slots in a 6-column grid
// (6x2). Owned sites fill from the top-left; the remainder render as faint
// "locked" placeholders you can unlock by buying. Chosen to comfortably hold
// the playable range — the Fibonacci purchase curve makes a 13th site cost
// tens of billions, so real portfolios stay within this. If a portfolio ever
// exceeds it (e.g. auction wins), the grid grows extra rows but never widens.
export const TOTAL_SITE_SLOTS = 12;
const GRID_COLUMNS = 6;

type SiteKind = "occupied" | "free-incoming" | "free" | "building" | "locked";

function SiteCube({
  kind,
  yearsLeft,
  size,
}: {
  kind: SiteKind;
  yearsLeft?: number;
  size: "sm" | "md";
}) {
  const dims = size === "md" ? "h-12 w-12" : "h-8 w-8";
  const icon = size === "md" ? "h-5 w-5" : "h-4 w-4";
  const base = `relative flex ${dims} items-center justify-center rounded-md border-2 transition-colors`;

  if (kind === "occupied") {
    return (
      <div
        title="Occupied — running a trial"
        className={`${base} border-teal-500 bg-teal-500 text-white`}
      >
        <FlaskConical className={icon} />
      </div>
    );
  }
  if (kind === "building") {
    return (
      <div
        title={`Under construction — ${yearsLeft} year${yearsLeft === 1 ? "" : "s"} left`}
        className={`${base} animate-pulse border-dashed border-amber-400 bg-amber-50 text-amber-600`}
      >
        <Hammer className={size === "md" ? "h-4 w-4" : "h-3 w-3"} />
        <span className="absolute -bottom-1.5 rounded-full bg-amber-500 px-1 text-[9px] leading-tight text-white">
          {yearsLeft}y
        </span>
      </div>
    );
  }
  if (kind === "free-incoming") {
    return (
      <div
        title="Free — an asset selected this year will start here next year"
        className={`${base} border-teal-400 bg-teal-50 text-teal-500 ring-2 ring-teal-400 ring-offset-1`}
      >
        <FlaskConical className={icon} />
      </div>
    );
  }
  if (kind === "free") {
    return (
      <div
        title="Free — available for a new trial"
        className={`${base} border-dashed border-gray-300 bg-gray-50 text-gray-300`}
      >
        <FlaskConical className={icon} />
      </div>
    );
  }
  // Locked: a slot you don't own yet. Faint, iconless placeholder to distinguish
  // it from an owned-but-free site (which shows a greyed flask).
  return (
    <div
      title="Not yet owned — buy a site to unlock"
      className={`${base} border-dotted border-gray-200 bg-transparent`}
    >
      <span className="h-1 w-1 rounded-full bg-gray-200" />
    </div>
  );
}

// A fixed 5-column grid of clinical-site slots. Owned sites fill from the top:
// occupied first, then free (incoming-highlighted before plain free), then
// sites under construction; the remaining slots up to TOTAL_SITE_SLOTS render
// as faint "locked" placeholders so the panel footprint never changes and the
// grid never extends horizontally. `incoming` free cubes light up teal to show
// assets selected this turn that will fill them next year (capped at
// free_sites).
export default function SiteCubes({
  sitesOccupied,
  freeSites,
  sitesInDevelopment,
  incoming = 0,
  size = "md",
}: {
  sitesOccupied: number;
  freeSites: number;
  sitesInDevelopment: number[];
  incoming?: number;
  size?: "sm" | "md";
}) {
  const highlighted = Math.min(Math.max(incoming, 0), freeSites);

  const cubes: { kind: SiteKind; yearsLeft?: number }[] = [];
  for (let i = 0; i < sitesOccupied; i++) cubes.push({ kind: "occupied" });
  for (let i = 0; i < freeSites; i++) {
    cubes.push({ kind: i < highlighted ? "free-incoming" : "free" });
  }
  for (const yearsLeft of sitesInDevelopment) {
    cubes.push({ kind: "building", yearsLeft });
  }

  // Fill the rest of the fixed footprint with locked placeholders. If real
  // sites already exceed the footprint, no placeholders are added and the grid
  // simply grows extra rows (still GRID_COLUMNS wide — never widens).
  const locked = Math.max(0, TOTAL_SITE_SLOTS - cubes.length);
  for (let i = 0; i < locked; i++) cubes.push({ kind: "locked" });

  // p-1 gives the ring-offset on incoming cubes room so it isn't clipped.
  return (
    <div
      className="grid w-fit gap-2 p-1"
      style={{
        gridTemplateColumns: `repeat(${GRID_COLUMNS}, minmax(0, max-content))`,
      }}
    >
      {cubes.map((c, i) => (
        <SiteCube key={i} kind={c.kind} yearsLeft={c.yearsLeft} size={size} />
      ))}
    </div>
  );
}
