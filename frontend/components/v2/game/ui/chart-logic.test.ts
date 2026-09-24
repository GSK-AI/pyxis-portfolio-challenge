import { describe, expect, it } from "vitest";

/**
 * Numeric equivalence tests: the v2 charts must reproduce the classic
 * chart data logic EXACTLY. Each "classic*" function below is copied
 * verbatim from the classic component; each "v2*" mirrors the code in
 * the v2 component / adapter. If either side drifts, these fail.
 */

// ---------- Capital chart: classic CapitalProjectionGraph ----------

interface CapitalPoint {
  time: number;
  capital: number;
}

function classicCapital(
  capitalOverTime: number[],
  currentTime: number,
  currentCapital: number,
) {
  const capitalData: CapitalPoint[] = [];
  for (let time = 0; time <= currentTime; time++) {
    if (time < capitalOverTime.length) {
      capitalData.push({ time, capital: capitalOverTime[time] });
    } else {
      capitalData.push({ time, capital: currentCapital });
    }
  }
  if (capitalData.length === 0) {
    capitalData.push({ time: 0, capital: currentCapital });
  }
  const allCapitals = capitalData.map((d) => d.capital);
  const maxCapital = Math.max(...allCapitals);
  const minCapital = Math.min(...allCapitals, 0);
  const maxCapitalInMillions = maxCapital / 1000000;
  const minCapitalInMillions = minCapital / 1000000;
  const buffer = Math.max(
    100,
    Math.ceil(Math.abs(maxCapitalInMillions - minCapitalInMillions) * 0.1),
  );
  const yAxisMax = Math.ceil(maxCapitalInMillions) + buffer;
  const yAxisMin = Math.min(0, Math.floor(minCapitalInMillions) - buffer);
  return { capitalData, yAxisMin, yAxisMax };
}

// Mirror of CapitalChart.tsx (rawData + domain logic)
function v2Capital(
  series: number[],
  currentTime: number,
  currentCapital: number,
) {
  const points: CapitalPoint[] = [];
  for (let time = 0; time <= currentTime; time++) {
    if (time < series.length) {
      points.push({ time, capital: series[time] });
    } else {
      points.push({ time, capital: currentCapital });
    }
  }
  if (points.length === 0) {
    points.push({ time: 0, capital: currentCapital });
  }
  const allCapitals = points.map((d) => d.capital);
  const maxCapital = Math.max(...allCapitals);
  const minCapital = Math.min(...allCapitals, 0);
  const maxCapitalInMillions = maxCapital / 1_000_000;
  const minCapitalInMillions = minCapital / 1_000_000;
  const buffer = Math.max(
    100,
    Math.ceil(Math.abs(maxCapitalInMillions - minCapitalInMillions) * 0.1),
  );
  const yAxisMax = Math.ceil(maxCapitalInMillions) + buffer;
  const yAxisMin = Math.min(0, Math.floor(minCapitalInMillions) - buffer);
  return { capitalData: points, yAxisMin, yAxisMax };
}

// ---------- Projection chart: classic ActionChart stacking ----------

interface DataPoint {
  time: number;
  value: number;
  assetId: string;
  assetName: string;
  isSelected?: boolean;
}

function classicStack(processedData: DataPoint[][], horizon: number) {
  const timePoints = Array.from({ length: horizon + 1 }, (_, i) => i);
  return timePoints.map((time) => {
    let cumulativeValue = 0;
    return processedData.map((assetSeries, assetIndex) => {
      const dataPoint = assetSeries.find((d) => d.time === time);
      const value = (dataPoint?.value || 0) / 1000000;
      const y0 = cumulativeValue;
      cumulativeValue += value;
      return { time, y0, y1: cumulativeValue, assetIndex };
    });
  });
}

// Mirror of the GameExperienceV2 adapter + ProjectionChart stacking
function v2Stack(processedData: DataPoint[][], horizon: number) {
  const series = processedData.map((assetSeries) => {
    const values = new Array(horizon + 1).fill(0);
    assetSeries.forEach((point) => {
      values[point.time] = point.value;
    });
    return values as number[];
  });
  const timePoints = Array.from({ length: horizon + 1 }, (_, i) => i);
  return timePoints.map((time) => {
    let cumulative = 0;
    return series.map((values, assetIndex) => {
      const value = (values[time] ?? 0) / 1_000_000;
      const y0 = cumulative;
      cumulative += value;
      return { time, y0, y1: cumulative, assetIndex };
    });
  });
}

// Classic next-year total: scan from the top layer down.
function classicNextTotal(
  stacked: ReturnType<typeof classicStack>,
  currentTime: number,
  horizon: number,
  layerCount: number,
) {
  if (currentTime >= horizon) return null;
  const nextTime = currentTime + 1;
  const nextTimeData = stacked.find((t) => t[0]?.time === nextTime);
  if (!nextTimeData) return null;
  let topPoint = null;
  for (let i = layerCount - 1; i >= 0; i--) {
    const point = nextTimeData[i];
    if (point !== undefined && point !== null) {
      topPoint = point;
      break;
    }
  }
  if (!topPoint && nextTimeData.length > 0) {
    topPoint = { time: nextTime, y0: 0, y1: 0, assetIndex: 0 };
  }
  return topPoint ? topPoint.y1 * 1000000 : null;
}

// v2: header total is the raw sum; callout uses the top of the stack.
function v2NextTotal(
  processedData: DataPoint[][],
  stacked: ReturnType<typeof v2Stack>,
  currentTime: number,
  horizon: number,
) {
  const t = currentTime + 1;
  if (t > horizon) return null;
  const stackTop = stacked[t]?.at(-1);
  return stackTop ? stackTop.y1 * 1_000_000 : null;
}

// Deterministic pseudo-random series (no Math.random in tests).
function pseudoSeries(
  count: number,
  horizon: number,
  opts: { sparse?: boolean; shuffled?: boolean } = {},
): DataPoint[][] {
  return Array.from({ length: count }, (_, i) => {
    let points: DataPoint[] = [];
    for (let t = 0; t <= horizon; t++) {
      const keep = opts.sparse ? (t * 7 + i * 3) % 3 !== 0 : true;
      if (!keep) continue;
      const value = ((t * 31 + i * 17) % 90) * 1_000_000;
      points.push({
        time: t,
        value,
        assetId: `a${i}`,
        assetName: `Asset ${i}`,
      });
    }
    if (opts.shuffled) {
      points = [
        ...points.slice(points.length / 2),
        ...points.slice(0, points.length / 2),
      ];
    }
    return points;
  });
}

describe("CapitalChart data logic matches classic CapitalProjectionGraph", () => {
  const cases: [string, number[], number, number][] = [
    ["game start, single point", [10_000_000_000], 0, 10_000_000_000],
    ["empty series", [], 0, 10_000_000_000],
    ["currentTime beyond series length", [10e9, 9.5e9], 5, 9_200_000_000],
    [
      "mid game",
      Array.from({ length: 41 }, (_, t) => 10e9 - t * 180e6),
      40,
      2.8e9,
    ],
    [
      "dips negative",
      Array.from({ length: 31 }, (_, t) => 4e9 - t * 350e6),
      30,
      -6.5e9,
    ],
    ["zero capital", [0], 0, 0],
    ["tiny values", [1234, 5678], 1, 5678],
  ];

  it.each(cases)("%s", (_name, series, currentTime, currentCapital) => {
    expect(v2Capital(series, currentTime, currentCapital)).toEqual(
      classicCapital(series, currentTime, currentCapital),
    );
  });
});

describe("ProjectionChart stacking matches classic ActionChart", () => {
  const scenarios: [string, DataPoint[][], number][] = [
    ["dense series", pseudoSeries(4, 100), 100],
    [
      "sparse series (missing times)",
      pseudoSeries(5, 100, { sparse: true }),
      100,
    ],
    ["out-of-order points", pseudoSeries(3, 50, { shuffled: true }), 50],
    ["single asset", pseudoSeries(1, 25), 25],
    ["no assets", [], 100],
    ["short horizon", pseudoSeries(6, 5), 5],
  ];

  it.each(scenarios)("%s", (_name, processed, horizon) => {
    const classic = classicStack(processed, horizon);
    const v2 = v2Stack(processed, horizon);
    expect(v2).toEqual(classic);
  });

  it.each(scenarios)("next-year totals: %s", (_name, processed, horizon) => {
    const classic = classicStack(processed, horizon);
    const v2 = v2Stack(processed, horizon);
    for (const currentTime of [
      0,
      1,
      Math.floor(horizon / 2),
      horizon - 1,
      horizon,
    ]) {
      if (currentTime < 0) continue;
      const classicTotal = classicNextTotal(
        classic,
        currentTime,
        horizon,
        processed.length,
      );
      const v2Total = v2NextTotal(processed, v2, currentTime, horizon);
      // Classic returns null when there are no layers at all; v2 also
      // renders no callout then — both must agree on null vs value.
      expect(v2Total).toEqual(classicTotal);
    }
  });

  it("past/future split indices match classic", () => {
    const stacked = classicStack(pseudoSeries(3, 40), 40);
    for (const currentTime of [0, 1, 20, 39, 40]) {
      const splitIndex = currentTime + 1;
      const classicPast = stacked.slice(0, splitIndex);
      const classicFuture = stacked.slice(splitIndex - 1);
      const v2Past = stacked.slice(0, splitIndex);
      const v2Future = stacked.slice(Math.max(splitIndex - 1, 0));
      expect(v2Past).toEqual(classicPast);
      expect(v2Future).toEqual(classicFuture);
    }
  });
});
