/**
 * Value label pinned to the current-position dot of a compact (sparkline)
 * chart. Compact charts drop their axes, so this is the only number on the
 * plot — it sits beside the dot, flips to the left near the right edge, and
 * is painted with a white halo so it stays legible over the area fill.
 */

/** Top of the plot the label may not ride above (keeps the glyphs inside the svg). */
const TOP_LIMIT = 10;
/** Gap between the dot and the label, horizontally and vertically. */
const GAP = 6;
/** ~6.5px per character at 11px bold — enough to know if it would overflow. */
const CHAR_WIDTH = 6.5;

/**
 * Where the label sits relative to its dot. Pure so the edge cases (right
 * overflow, a dot pinned to the top of the plot) are testable without a DOM.
 */
export function sparkValuePlacement({
  x,
  y,
  width,
  label,
}: {
  x: number;
  y: number;
  /** Plot width, used to flip the label inward at the right edge. */
  width: number;
  label: string;
}) {
  const flip = x + label.length * CHAR_WIDTH + GAP + 2 > width;
  return {
    x: flip ? x - GAP - 1 : x + GAP + 1,
    y: Math.max(y - GAP, TOP_LIMIT),
    textAnchor: flip ? ("end" as const) : ("start" as const),
  };
}

export function SparkValue({
  x,
  y,
  width,
  label,
  fill = "#3e71d2",
}: {
  x: number;
  y: number;
  width: number;
  label: string;
  fill?: string;
}) {
  const placed = sparkValuePlacement({ x, y, width, label });

  return (
    <text
      x={placed.x}
      y={placed.y}
      fontSize={11}
      fontWeight={700}
      fill={fill}
      textAnchor={placed.textAnchor}
      stroke="#ffffff"
      strokeWidth={3}
      strokeLinejoin="round"
      paintOrder="stroke"
    >
      {label}
    </text>
  );
}
