"use client";

import { useMemo } from "react";
import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
import { LinePath, Circle, Line } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import type { PlaythroughData } from "@/lib/definitionsGameZ";
import { formatDisplayNumber } from "@/lib/numbers";

/**
 * v2 net-cash-flow-over-time chart for the replay viewer. The per-agent
 * series construction, bankruptcy cutoff, and y-domain buffer are
 * IDENTICAL to the classic RewardChart — only the presentation changed
 * (quiet grid, v2 tick color, responsive width).
 */

const TICK = "#9aa0ab";
const MARGIN = { top: 16, right: 16, bottom: 32, left: 56 };

interface DataPoint {
  step: number;
  value: number;
}

interface ReplayRewardChartProps {
  data: PlaythroughData;
  currentStepIndex: number;
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
  height?: number;
}

function Chart({
  width,
  height,
  data,
  currentStepIndex,
  agentColors,
}: ReplayRewardChartProps & { width: number; height: number }) {
  // --- identical data logic to the classic RewardChart ---
  const agentSeries = useMemo(() => {
    const series: Record<string, DataPoint[]> = {};
    for (const agentId of data.metadata.agent_ids) {
      const points: DataPoint[] = [{ step: 0, value: 0 }];
      for (const stepRecord of data.steps) {
        points.push({
          step: stepRecord.step,
          value: stepRecord.cumulative_rewards[agentId] ?? 0,
        });
        // Stop plotting if this agent went bankrupt
        const agentState = stepRecord.agent_states[agentId];
        if (
          agentState?.game_ended &&
          !agentState?.ended_reason?.includes("horizon")
        ) {
          break;
        }
      }
      series[agentId] = points;
    }
    return series;
  }, [data]);

  const { yMin, yMax } = useMemo(() => {
    let min = 0;
    let max = 0;
    for (const points of Object.values(agentSeries)) {
      for (const p of points) {
        if (p.value < min) min = p.value;
        if (p.value > max) max = p.value;
      }
    }
    const range = max - min || 1;
    const buffer = range * 0.1;
    return { yMin: min - buffer, yMax: max + buffer };
  }, [agentSeries]);

  const totalSteps = data.steps.length;
  const maxStep =
    totalSteps > 0 ? data.steps[totalSteps - 1].step : data.metadata.horizon;

  const currentStep =
    currentStepIndex === 0 ? 0 : (data.steps[currentStepIndex - 1]?.step ?? 0);
  // --- end identical data logic ---

  const innerHeight = height - MARGIN.top - MARGIN.bottom;
  const xScale = scaleLinear({
    range: [MARGIN.left, width - MARGIN.right],
    domain: [0, maxStep],
    nice: false,
  });
  const yScale = scaleLinear({
    range: [innerHeight + MARGIN.top, MARGIN.top],
    domain: [yMin / 1_000_000, yMax / 1_000_000],
    nice: true,
  });

  const getX = (d: DataPoint) => xScale(d.step);
  const getY = (d: DataPoint) => yScale(d.value / 1_000_000);

  return (
    <svg width={width} height={height}>
      <Group>
        <GridRows
          left={MARGIN.left}
          width={width - MARGIN.left - MARGIN.right}
          scale={yScale}
          numTicks={4}
          stroke="#000000"
          strokeOpacity={0.05}
        />

        <AxisBottom
          top={innerHeight + MARGIN.top}
          scale={xScale}
          hideTicks
          stroke="#d5d7db"
          numTicks={Math.min(maxStep, Math.max(5, Math.ceil(maxStep / 50)))}
          tickLabelProps={() => ({
            fill: TICK,
            fontSize: 10,
            textAnchor: "middle",
          })}
        />
        <AxisLeft
          left={MARGIN.left}
          scale={yScale}
          numTicks={4}
          hideTicks
          hideAxisLine
          tickFormat={(v) => formatDisplayNumber(Number(v) * 1_000_000)}
          tickLabelProps={() => ({
            fill: TICK,
            fontSize: 10,
            textAnchor: "end",
            dx: "-0.25em",
            dy: "0.25em",
          })}
        />

        {/* Zero line */}
        {yMin < 0 && (
          <Line
            from={{ x: MARGIN.left, y: yScale(0) }}
            to={{ x: width - MARGIN.right, y: yScale(0) }}
            stroke="#d5d7db"
            strokeWidth={1}
            strokeDasharray="4 2"
          />
        )}

        {/* Current step marker */}
        {currentStepIndex > 0 && (
          <Line
            from={{ x: xScale(currentStep), y: MARGIN.top }}
            to={{ x: xScale(currentStep), y: innerHeight + MARGIN.top }}
            stroke={TICK}
            strokeWidth={1}
            strokeDasharray="4 3"
          />
        )}

        {data.metadata.agent_ids.map((agentId) => {
          const points = agentSeries[agentId];
          const color = agentColors[agentId];
          const currentPoint = points[currentStepIndex];
          return (
            <Group key={agentId}>
              <LinePath
                data={points}
                x={getX}
                y={getY}
                stroke={color}
                strokeWidth={2}
                curve={curveLinear}
              />
              {currentPoint && (
                <Circle
                  cx={getX(currentPoint)}
                  cy={getY(currentPoint)}
                  r={5}
                  fill={color}
                  stroke="#fff"
                  strokeWidth={2}
                />
              )}
            </Group>
          );
        })}
      </Group>
    </svg>
  );
}

export function ReplayRewardChart({
  height = 260,
  ...props
}: ReplayRewardChartProps) {
  return (
    <div>
      <div style={{ height }}>
        <ParentSize debounceTime={10}>
          {({ width }) =>
            width > 0 ? (
              <Chart {...props} width={width} height={height} />
            ) : null
          }
        </ParentSize>
      </div>

      {/* Legend */}
      <div className="mt-2 flex flex-wrap gap-4">
        {props.data.metadata.agent_ids.map((agentId) => (
          <div key={agentId} className="flex items-center gap-1.5">
            <span
              className="size-2.5 rounded-full"
              style={{ backgroundColor: props.agentColors[agentId] }}
            />
            <span className="text-xs text-muted-foreground">
              {props.agentDisplayNames[agentId] ?? agentId}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
