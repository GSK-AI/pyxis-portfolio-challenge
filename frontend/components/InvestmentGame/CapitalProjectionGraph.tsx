"use client";

import { scaleLinear } from "@visx/scale";
import { LinePath, Circle } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { format } from "@visx/vendor/d3-format";

import type { GameStepSchemaType } from "@/lib/definitionsGameZ";
import {
  visualisationConsts,
  getInnerDimensions,
} from "@/lib/visualisations/helpers";
import { formatDisplayNumber } from "@/lib/numbers";
import { InformationButton } from "../InformationButton";
import { informationDictionary } from "@/lib/information-dictionary-game";

interface CapitalProjectionGraphProps {
  currentTime: number;
  currentCapital: number;
  totalTime: number;
  gameState?: GameStepSchemaType;
  height?: number;
  width?: number;
  margin?: { top: number; right: number; bottom: number; left: number };
}

interface CapitalDataPoint {
  time: number;
  capital: number;
}

export default function CapitalProjectionGraph({
  currentTime,
  currentCapital,
  totalTime,
  gameState,
  height = 200,
  width = 300,
  margin = { top: 40, right: 30, bottom: 50, left: 60 },
}: CapitalProjectionGraphProps) {
  const { colors } = visualisationConsts;
  const { innerHeight } = getInnerDimensions({
    width,
    height,
    margin,
  });

  // Use capital_over_time from game state for historical data
  const capitalOverTime = gameState?.capital_over_time || [];

  const capitalData: CapitalDataPoint[] = [];

  // Historical data points only
  for (let time = 0; time <= currentTime; time++) {
    if (time < capitalOverTime.length) {
      capitalData.push({ time, capital: capitalOverTime[time] });
    } else {
      capitalData.push({ time, capital: currentCapital });
    }
  }

  // Ensure we have at least current time
  if (capitalData.length === 0) {
    capitalData.push({ time: 0, capital: currentCapital });
  }

  // Calculate Y-axis bounds from historical data only
  const allCapitals = capitalData.map((d) => d.capital);
  const maxCapital = Math.max(...allCapitals);
  const minCapital = Math.min(...allCapitals, 0);

  const maxCapitalInMillions = maxCapital / 1000000;
  const minCapitalInMillions = minCapital / 1000000;

  const buffer = Math.max(
    100,
    Math.ceil(Math.abs(maxCapitalInMillions - minCapitalInMillions) * 0.1),
  );

  let yAxisMax = Math.ceil(maxCapitalInMillions) + buffer;
  let yAxisMin = Math.min(0, Math.floor(minCapitalInMillions) - buffer);

  // Create scales
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

  const formatTime = format("");
  const formatValue = (value: any) => {
    const numValue = Number(value);
    const actualValue = numValue * 1000000;
    return formatDisplayNumber(actualValue);
  };

  const getX = (d: CapitalDataPoint) => xScale(d.time);
  const getY = (d: CapitalDataPoint) => yScale(d.capital / 1000000);

  return (
    <div className="rounded-lg bg-gray-50 p-2">
      <div className="flex items-center gap-2">
        <h3 className="font-light text-gray-600"></h3>
        <InformationButton
          title={informationDictionary.capitalPlot.title}
          description={informationDictionary.capitalPlot.description}
          buttonClassName="w-4 h-4"
        />
      </div>
      <svg width={width} height={height}>
        <Group>
          {/* X Axis at y=0 */}
          <AxisBottom
            top={yScale(0)}
            scale={xScale}
            hideTicks={true}
            tickFormat={formatTime}
            numTicks={Math.min(
              totalTime,
              Math.max(5, Math.ceil(totalTime / 10)),
            )}
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
            tickFormat={formatValue}
            numTicks={4}
            hideTicks={true}
            tickLabelProps={() => ({
              fill: colors.axisTicks,
              fontSize: 10,
              textAnchor: "end",
              dx: "-0.25em",
              dy: "0.25em",
            })}
          />
          <text x={margin.left} y="15" fontSize={12} fill={colors.axisTicks}>
            (Capital)
          </text>

          {/* Capital line */}
          <LinePath
            data={capitalData}
            x={getX}
            y={getY}
            stroke="#0d9488"
            strokeWidth={2}
            curve={curveLinear}
          />

          {/* Current position dot */}
          {capitalData.length > 0 && (
            <Circle
              cx={getX(capitalData[capitalData.length - 1])}
              cy={getY(capitalData[capitalData.length - 1])}
              r={6}
              fill="rgb(37 137 254)"
              stroke="#ffffff"
              strokeWidth={2}
            />
          )}
        </Group>
      </svg>
    </div>
  );
}
