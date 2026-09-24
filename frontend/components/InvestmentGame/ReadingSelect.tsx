"use client";

import { formatDisplayNumber } from "@/lib/numbers";

// Reading selector for PTRS diligence: per step, per asset you commission 0..N
// concurrent readings. A dropdown picks the count and the cumulative cost updates
// live next to it.
//
// costs holds the cumulative cost curve (index i = total cost of i+1 readings),
// so its length is the reading cap. affordableUpTo is the highest count that
// still fits cash given the rest of the player's selections; options above it are
// disabled unless they would step the selection *down*.
export default function ReadingSelect({
  count,
  costs,
  affordableUpTo,
  onSet,
  assetName,
}: {
  count: number;
  costs: number[];
  affordableUpTo: number;
  onSet: (count: number) => void;
  assetName: string;
}) {
  const maxReadings = costs.length;
  const selectedCost = count <= 0 ? 0 : (costs[count - 1] ?? 0);
  const overCash = count > affordableUpTo;

  return (
    <div className="flex items-center gap-2">
      <select
        aria-label={`PTRS readings on ${assetName}`}
        value={count}
        onChange={(e) => onSet(Number(e.target.value))}
        className="rounded border border-gray-300 bg-white px-1.5 py-1 text-xs font-semibold text-gray-800 focus:border-sky-400 focus:outline-none"
      >
        {Array.from({ length: maxReadings + 1 }, (_, n) => (
          <option
            key={n}
            value={n}
            // Never block picking a lower count; only gate growth on cash.
            disabled={n > count && n > affordableUpTo}
          >
            {n} {n === 1 ? "reading" : "readings"}
          </option>
        ))}
      </select>
      <span
        className={`whitespace-nowrap text-[11px] font-medium tabular-nums ${
          overCash ? "text-red-600" : "text-gray-500"
        }`}
      >
        {count > 0 ? `£${formatDisplayNumber(selectedCost)}` : "free"}
      </span>
    </div>
  );
}
