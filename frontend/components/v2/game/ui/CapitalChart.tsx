"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
import { AreaClosed, LinePath, Circle } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { LinearGradient } from "@visx/gradient";
import { Group } from "@visx/group";
import { formatDisplayNumber } from "@/lib/numbers";
import { SparkValue } from "./SparkValue";

/**
 * v2 capital chart. Data preparation is IDENTICAL to the classic
 * CapitalProjectionGraph (historical series fill, y-domain buffer in
 * millions, x-axis anchored at zero) — only the presentation changed:
 * responsive width, chambray line with soft area fill, quiet grid.
 */

const CHAMBRAY = "#3e71d2";
const TICK = "#9aa0ab";
const MARGIN = { top: 12, right: 12, bottom: 28, left: 48 };
/** Compact: no axes to make room for, so the shape fills the box. */
const COMPACT_MARGIN = { top: 6, right: 6, bottom: 6, left: 6 };

interface CapitalDataPoint {
  time: number;
  capital: number;
}

/**
 * Tween the newly appended year: the last point glides from the previous
 * year's position to its final value (~600ms ease-out). Everything derived
 * from the returned series (line, area, dot, y-domain) animates with it.
 */
function useAnimatedSeries(data: CapitalDataPoint[]) {
  const [display, setDisplay] = useState(data);
  const prevRef = useRef(data);
  const dataKey = `${data.length}:${data[data.length - 1]?.capital ?? 0}`;

  useEffect(() => {
    const prev = prevRef.current;
    prevRef.current = data;
    if (data.length <= prev.length || prev.length === 0) {
      setDisplay(data);
      return;
    }
    const from = prev[prev.length - 1];
    const target = data[data.length - 1];
    const start = performance.now();
    const duration = 600;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay([
        ...data.slice(0, -1),
        {
          time: from.time + (target.time - from.time) * eased,
          capital: from.capital + (target.capital - from.capital) * eased,
        },
      ]);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataKey]);

  return display;
}

interface CapitalChartProps {
  /** capital_over_time from game state. */
  series: number[];
  currentTime: number;
  currentCapital: number;
  totalTime: number;
  height?: number;
  /** Sparkline mode: own header line, no axes, no labels. */
  compact?: boolean;
  className?: string;
}

function Chart({
  width,
  height,
  series,
  currentTime,
  currentCapital,
  totalTime,
  compact,
}: CapitalChartProps & { width: number; height: number }) {
  // --- identical data logic to the classic graph ---
  const rawData = useMemo(() => {
    const points: CapitalDataPoint[] = [];
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
    return points;
  }, [series, currentTime, currentCapital]);
  const capitalData = useAnimatedSeries(rawData);

  const allCapitals = capitalData.map((d) => d.capital);
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
  // --- end identical data logic ---

  const margin = compact ? COMPACT_MARGIN : MARGIN;
  const innerHeight = height - margin.top - margin.bottom;
  const xScale = scaleLinear({
    range: [margin.left, width - margin.right],
    domain: [0, totalTime],
    nice: false,
  });
  const yScale = scaleLinear({
    range: [innerHeight + margin.top, margin.top],
    domain: [yAxisMin, yAxisMax],
    nice: false,
  });

  const getX = (d: CapitalDataPoint) => xScale(d.time);
  const getY = (d: CapitalDataPoint) => yScale(d.capital / 1_000_000);
  const formatValue = (value: unknown) =>
    formatDisplayNumber(Number(value) * 1_000_000);
  const last = capitalData[capitalData.length - 1];

  return (
    <svg width={width} height={height}>
      <LinearGradient
        id="capital-area"
        from={CHAMBRAY}
        to={CHAMBRAY}
        fromOpacity={0.18}
        toOpacity={0.02}
      />
      <Group>
        {/* Compact is a bare sparkline: no grid, no axes, clean ground. */}
        {!compact && (
          <GridRows
            left={margin.left}
            width={width - margin.left - margin.right}
            scale={yScale}
            numTicks={4}
            stroke="#000000"
            strokeOpacity={0.05}
          />
        )}

        <AreaClosed
          data={capitalData}
          x={getX}
          y={getY}
          yScale={yScale}
          curve={curveLinear}
          fill="url(#capital-area)"
        />
        <LinePath
          data={capitalData}
          x={getX}
          y={getY}
          stroke={CHAMBRAY}
          strokeWidth={2}
          curve={curveLinear}
        />

        {!compact && (
          <>
            <AxisBottom
              top={yScale(0)}
              scale={xScale}
              hideTicks
              stroke="#d5d7db"
              numTicks={Math.min(
                totalTime,
                Math.max(5, Math.ceil(totalTime / 20)),
              )}
              tickLabelProps={() => ({
                fill: TICK,
                fontSize: 10,
                textAnchor: "middle",
              })}
            />
            <text
              x={MARGIN.left}
              y={MARGIN.top - 2}
              fontSize={10}
              fill={TICK}
              opacity={0.8}
            >
              Capital
            </text>
            <AxisLeft
              left={MARGIN.left}
              scale={yScale}
              tickFormat={formatValue}
              numTicks={4}
              hideTicks
              hideAxisLine
              tickLabelProps={() => ({
                fill: TICK,
                fontSize: 10,
                textAnchor: "end",
                dx: "-0.25em",
                dy: "0.25em",
              })}
            />
          </>
        )}

        <Circle
          cx={getX(last)}
          cy={getY(last)}
          r={compact ? 3 : 5}
          fill={CHAMBRAY}
          stroke="#ffffff"
          strokeWidth={compact ? 1.5 : 2}
        />
        {compact && (
          <SparkValue
            x={getX(last)}
            y={getY(last)}
            width={width}
            label={`£${formatDisplayNumber(last.capital)}`}
          />
        )}
      </Group>
    </svg>
  );
}

export function CapitalChart({
  height = 200,
  className,
  ...props
}: CapitalChartProps) {
  const plot = (
    <div style={{ height }}>
      <ParentSize debounceTime={10}>
        {({ width }) =>
          width > 0 ? <Chart {...props} width={width} height={height} /> : null
        }
      </ParentSize>
    </div>
  );

  // Compact mirrors ProjectionChart's header (label only — the value rides
  // on the dot) so a row of mini charts lines up whatever is in the box.
  if (props.compact) {
    return (
      <div className={className}>
        <div className="truncate pb-0.5 text-[11px] text-muted-foreground">
          Capital
        </div>
        {plot}
      </div>
    );
  }

  return <div className={className}>{plot}</div>;
}
