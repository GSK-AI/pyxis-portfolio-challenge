"use client";

import { useMemo } from "react";
import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
import { AreaClosed, Circle } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { formatDisplayNumber } from "@/lib/numbers";
import { InfoHint } from "./InfoHint";
import { SparkValue } from "./SparkValue";

/**
 * v2 projection chart — "Total Cost this year" / "Budget next year".
 * Stacking logic is IDENTICAL to the classic ActionChart (cumulative
 * per-time layers in millions, past/future split at currentTime, next-year
 * callout on the top of the stack). Presentation is new: responsive width,
 * chambray layer palette, quiet grid, pill-style next-year label.
 * Feed it the per-asset series produced by processAssetDataForChart.
 */

export interface ProjectionSeries {
  id: string;
  name: string;
  selected?: boolean;
  /** Value in GBP for each time step 0..horizon. */
  values: number[];
}

interface StackedPoint {
  time: number;
  y0: number;
  y1: number;
}

const TICK = "#9aa0ab";
const MARGIN = { top: 12, right: 16, bottom: 28, left: 48 };
/** Compact: no axes to make room for, so the stack fills the box. */
const COMPACT_MARGIN = { top: 6, right: 6, bottom: 6, left: 6 };

const pastColor = (i: number, total: number) =>
  `hsl(219, 62%, ${46 - (i / Math.max(total - 1, 1)) * 10}%)`;
const futureColor = (i: number, total: number) =>
  `hsl(219, 65%, ${82 - (i / Math.max(total - 1, 1)) * 14}%)`;

interface ProjectionChartProps {
  title: string;
  axisLabel: string;
  series: ProjectionSeries[];
  horizon: number;
  currentTime: number;
  /** Y-axis max in millions; pass calculateChartYAxisMax at integration. */
  yAxisMax?: number;
  info?: { title: string; description: string };
  height?: number;
  /** Sparkline mode: tight header, no axes, no next-year callout. */
  compact?: boolean;
  className?: string;
}

function Chart({
  width,
  height,
  series,
  horizon,
  currentTime,
  axisLabel,
  yAxisMax,
  compact,
}: Omit<ProjectionChartProps, "title" | "className" | "info"> & {
  width: number;
  height: number;
}) {
  // --- identical stacking logic to the classic ActionChart ---
  const stacked = useMemo(() => {
    const timePoints = Array.from({ length: horizon + 1 }, (_, i) => i);
    return timePoints.map((time) => {
      let cumulative = 0;
      return series.map((s) => {
        const value = (s.values[time] ?? 0) / 1_000_000;
        const y0 = cumulative;
        cumulative += value;
        return { time, y0, y1: cumulative } as StackedPoint;
      });
    });
  }, [series, horizon]);

  const domainMax = useMemo(() => {
    if (yAxisMax !== undefined) return yAxisMax;
    const maxTotal = Math.max(
      10,
      ...stacked.map((layers) => layers[layers.length - 1]?.y1 ?? 0),
    );
    return maxTotal * 1.2;
  }, [stacked, yAxisMax]);

  const splitIndex = currentTime + 1;
  const pastData = stacked.slice(0, splitIndex);
  const futureData = stacked.slice(Math.max(splitIndex - 1, 0));
  // --- end identical logic ---

  const margin = compact ? COMPACT_MARGIN : MARGIN;
  const innerHeight = height - margin.top - margin.bottom;
  const xScale = scaleLinear({
    range: [margin.left, width - margin.right],
    domain: [0, horizon],
    nice: false,
  });
  const yScale = scaleLinear({
    range: [innerHeight + margin.top, margin.top],
    domain: [0, domainMax],
    nice: false,
  });

  const formatValue = (value: unknown) =>
    formatDisplayNumber(Number(value) * 1_000_000);

  const currentTop = stacked[currentTime]?.at(-1);
  const nextTime = currentTime + 1;
  const nextTop = nextTime <= horizon ? stacked[nextTime]?.at(-1) : undefined;
  const nextValue = (nextTop?.y1 ?? 0) * 1_000_000;
  const nextLabel =
    nextValue === 0 ? "£0" : `£${formatDisplayNumber(nextValue)}`;
  const labelWidth = Math.max(nextLabel.length * 6.5 + 12, 44);

  return (
    <svg width={width} height={height}>
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

        {/* future layers first (lighter), past painted on top */}
        {series.map((s, i) =>
          futureData.length > 1 ? (
            <AreaClosed
              key={`future-${s.id}`}
              data={futureData.map((layers) => layers[i]).filter(Boolean)}
              x={(d) => xScale((d as StackedPoint).time)}
              y={(d) => yScale((d as StackedPoint).y1)}
              y0={(d) => yScale((d as StackedPoint).y0)}
              yScale={yScale}
              curve={curveLinear}
              fill={futureColor(i, series.length)}
            />
          ) : null,
        )}
        {series.map((s, i) =>
          pastData.length > 0 ? (
            <AreaClosed
              key={`past-${s.id}`}
              data={pastData.map((layers) => layers[i]).filter(Boolean)}
              x={(d) => xScale((d as StackedPoint).time)}
              y={(d) => yScale((d as StackedPoint).y1)}
              y0={(d) => yScale((d as StackedPoint).y0)}
              yScale={yScale}
              curve={curveLinear}
              fill={pastColor(i, series.length)}
            />
          ) : null,
        )}

        {!compact && (
          <>
            <AxisBottom
              top={innerHeight + MARGIN.top}
              scale={xScale}
              hideTicks
              stroke="#d5d7db"
              numTicks={Math.min(horizon, Math.max(5, Math.ceil(horizon / 20)))}
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
              {axisLabel}
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

        {/* current position dot */}
        {currentTop && (
          <Circle
            cx={xScale(currentTop.time)}
            cy={yScale(currentTop.y1)}
            r={compact ? 3 : 5}
            fill="#3e71d2"
            stroke="#ffffff"
            strokeWidth={compact ? 1.5 : 2}
          />
        )}
        {/* Final year: there is no next-year dot to label, so the current
            one carries the number instead of the box going blank. */}
        {compact && !nextTop && currentTop && (
          <SparkValue
            x={xScale(currentTop.time)}
            y={yScale(currentTop.y1)}
            width={width}
            label={`£${formatDisplayNumber(currentTop.y1 * 1_000_000)}`}
          />
        )}

        {/* next-year callout: hollow dot + pill label above. Compact swaps
            the pill for a bare number beside the dot. */}
        {nextTop && compact && (
          <>
            <Circle
              cx={xScale(nextTop.time)}
              cy={yScale(nextTop.y1)}
              r={2.5}
              fill="#ffffff"
              stroke="#3e71d2"
              strokeWidth={1.25}
            />
            <SparkValue
              x={xScale(nextTop.time)}
              y={yScale(nextTop.y1)}
              width={width}
              label={nextLabel}
            />
          </>
        )}
        {nextTop && !compact && (
          <Group>
            <Circle
              cx={xScale(nextTop.time)}
              cy={yScale(nextTop.y1)}
              r={4}
              fill="#ffffff"
              stroke="#3e71d2"
              strokeWidth={1.5}
            />
            <line
              x1={xScale(nextTop.time)}
              y1={yScale(nextTop.y1) - 5}
              x2={xScale(nextTop.time)}
              y2={yScale(nextTop.y1) - 16}
              stroke="#3e71d2"
              strokeOpacity={0.4}
            />
            <rect
              x={xScale(nextTop.time) - labelWidth / 2}
              y={yScale(nextTop.y1) - 34}
              width={labelWidth}
              height={18}
              rx={9}
              fill="#ffffff"
              stroke="#c7def6"
            />
            <text
              x={xScale(nextTop.time)}
              y={yScale(nextTop.y1) - 21}
              textAnchor="middle"
              fontSize={11}
              fontWeight={700}
              fill="#3e71d2"
            >
              {nextLabel}
            </text>
          </Group>
        )}
      </Group>
    </svg>
  );
}

export function ProjectionChart({
  title,
  info,
  height = 200,
  className,
  ...props
}: ProjectionChartProps) {
  const nextTotal = useMemo(() => {
    const t = props.currentTime + 1;
    if (t > props.horizon) return 0;
    return props.series.reduce((sum, s) => sum + (s.values[t] ?? 0), 0);
  }, [props.series, props.currentTime, props.horizon]);

  const total = nextTotal === 0 ? "£0" : `£${formatDisplayNumber(nextTotal)}`;

  return (
    <div className={className}>
      {props.compact ? (
        // Label only — the value rides on the dot, where the eye already is.
        <div className="truncate pb-0.5 text-[11px] text-muted-foreground">
          {title.replace(/:$/, "")}
        </div>
      ) : (
        <div className="flex items-baseline gap-2 px-1 pb-1 text-sm">
          <span className="text-muted-foreground">{title}</span>
          <span className="font-bold tabular-nums">{total}</span>
          {info && <InfoHint {...info} className="self-center" />}
        </div>
      )}
      <div style={{ height }}>
        <ParentSize debounceTime={10}>
          {({ width }) =>
            width > 0 ? (
              <Chart {...props} width={width} height={height} />
            ) : null
          }
        </ParentSize>
      </div>
    </div>
  );
}
