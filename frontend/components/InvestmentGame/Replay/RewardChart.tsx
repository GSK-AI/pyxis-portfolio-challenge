"use client";

import { useMemo } from "react";
import { scaleLinear } from "@visx/scale";
import { LinePath, Circle, Line } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { useParentSize } from "@visx/responsive";

import type { PlaythroughData } from "@/lib/definitionsGameZ";
import {
  visualisationConsts,
  getInnerDimensions,
} from "@/lib/visualisations/helpers";
import { formatDisplayNumber } from "@/lib/numbers";

interface RewardChartProps {
  data: PlaythroughData;
  currentStepIndex: number;
  agentColors: Record<string, string>;
  agentDisplayNames: Record<string, string>;
  height?: number;
}

interface DataPoint {
  step: number;
  value: number;
}

export default function RewardChart({
  data,
  currentStepIndex,
  agentColors,
  agentDisplayNames,
  height = 220,
}: RewardChartProps) {
  const { parentRef, width: parentWidth } = useParentSize({
    debounceTime: 150,
  });
  const width = Math.max(parentWidth || 600, 400);
  const margin = { top: 30, right: 30, bottom: 40, left: 70 };
  const { colors } = visualisationConsts;
  const { innerHeight } = getInnerDimensions({ width, height, margin });

  // Build time series per agent, stopping at bankruptcy
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

  // Compute Y domain from all data
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

  const xScale = scaleLinear({
    range: [margin.left, width - margin.right],
    domain: [0, maxStep],
    nice: false,
  });

  const yMinM = yMin / 1_000_000;
  const yMaxM = yMax / 1_000_000;

  const yScale = scaleLinear({
    range: [innerHeight + margin.top, margin.top],
    domain: [yMinM, yMaxM],
    nice: true,
  });

  const getX = (d: DataPoint) => xScale(d.step);
  const getY = (d: DataPoint) => yScale(d.value / 1_000_000);

  // Current step marker position
  const currentStep =
    currentStepIndex === 0 ? 0 : (data.steps[currentStepIndex - 1]?.step ?? 0);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-gray-700">
        Net Cash Flow Over Time
      </h3>
      <div ref={parentRef}>
        <svg width={width} height={height}>
          <Group>
            {/* X Axis */}
            <AxisBottom
              top={innerHeight + margin.top}
              scale={xScale}
              numTicks={Math.min(maxStep, Math.max(5, Math.ceil(maxStep / 50)))}
              tickLabelProps={() => ({
                fill: colors.axisTicks,
                fontSize: 10,
                textAnchor: "middle",
              })}
            />

            {/* Y Axis */}
            <AxisLeft
              left={margin.left}
              scale={yScale}
              numTicks={5}
              hideTicks
              tickFormat={(v) => formatDisplayNumber(Number(v) * 1_000_000)}
              tickLabelProps={() => ({
                fill: colors.axisTicks,
                fontSize: 10,
                textAnchor: "end",
                dx: "-0.25em",
                dy: "0.25em",
              })}
            />

            {/* Zero line */}
            {yMinM < 0 && (
              <Line
                from={{ x: margin.left, y: yScale(0) }}
                to={{ x: width - margin.right, y: yScale(0) }}
                stroke="#e0e0e0"
                strokeWidth={1}
                strokeDasharray="4 2"
              />
            )}

            {/* Current step vertical marker */}
            {currentStepIndex > 0 && (
              <Line
                from={{ x: xScale(currentStep), y: margin.top }}
                to={{
                  x: xScale(currentStep),
                  y: innerHeight + margin.top,
                }}
                stroke="#888"
                strokeWidth={1}
                strokeDasharray="4 3"
              />
            )}

            {/* Agent lines */}
            {data.metadata.agent_ids.map((agentId) => {
              const points = agentSeries[agentId];
              const color = agentColors[agentId];

              // Find the point at current step for the dot
              const currentPointIndex = currentStepIndex;
              const currentPoint = points[currentPointIndex];

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
      </div>

      {/* Legend */}
      <div className="mt-2 flex flex-wrap gap-4">
        {data.metadata.agent_ids.map((agentId) => (
          <div key={agentId} className="flex items-center gap-1.5">
            <div
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: agentColors[agentId] }}
            />
            <span className="text-xs text-gray-600">
              {agentDisplayNames[agentId] ?? agentId}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
