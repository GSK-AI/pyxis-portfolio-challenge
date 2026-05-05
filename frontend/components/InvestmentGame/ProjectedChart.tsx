import React from "react";
import { Group } from "@visx/group";
import { LinePath } from "@visx/shape";
import { scaleLinear } from "@visx/scale";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows, GridColumns } from "@visx/grid";
import { curveMonotoneX } from "@visx/curve";
import { formatDisplayNumber } from "@/lib/numbers";
import { visualisationConsts } from "@/lib/visualisations/helpers";

interface ProjectedChartProps {
  data: number[];
  dataType: "cost" | "revenue";
  title?: string;
  showGrid?: boolean;
}

interface DataPoint {
  step: number;
  value: number;
}

export default function ProjectedChart({
  data,
  dataType,
  title,
  showGrid = false,
}: ProjectedChartProps) {
  const { colors } = visualisationConsts;

  // Prepare data
  const chartData: DataPoint[] = data.map((value, idx) => ({
    step: idx + 1,
    value: value,
  }));

  // Chart dimensions
  const width = 400;
  const height = 150;
  const margin = { top: 10, right: 20, bottom: 50, left: 50 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const horizon = chartData.length;
  const maxValue = Math.max(...data);
  const yAxisMax = maxValue * 1.1;

  // Scales
  const xScale = scaleLinear<number>({
    domain: [1, Math.max(horizon, 1)],
    range: [0, innerWidth],
  });

  const yScale = scaleLinear<number>({
    domain: [0, yAxisMax],
    range: [innerHeight, 0],
  });

  // Accessors
  const getX = (d: DataPoint) => xScale(d.step);
  const getY = (d: DataPoint) => yScale(d.value);

  // Format functions
  const formatTime = (value: any) => `${value}`;
  const formatValue = (value: any) => {
    const numValue = Number(value);
    return formatDisplayNumber(numValue);
  };

  // Choose color based on data type
  const lineColor =
    dataType === "cost" ? colors.plotHighlightSecondary : colors.plotHighlight;

  return (
    <div className="w-full">
      {title && (
        <h4 className="mb-3 text-sm font-medium text-gray-700">{title}</h4>
      )}
      <svg width={width} height={height}>
        <Group left={margin.left} top={margin.top}>
          {/* Grid Lines (Optional) */}
          {showGrid && (
            <>
              {/* Y-axis Grid Lines (Horizontal) */}
              <GridRows
                scale={yScale}
                width={innerWidth}
                stroke={colors.axisStroke}
                strokeDasharray="4,4"
                numTicks={4}
              />

              {/* X-axis Grid Lines (Vertical) */}
              <GridColumns
                scale={xScale}
                height={innerHeight}
                stroke={colors.axisStroke}
                strokeDasharray="4,4"
                numTicks={Math.min(
                  horizon,
                  Math.max(5, Math.ceil(horizon / 4)),
                )}
              />
            </>
          )}

          {/* Main line */}
          <LinePath
            data={chartData}
            x={getX}
            y={getY}
            stroke={lineColor}
            strokeWidth={3}
            curve={curveMonotoneX}
          />

          {/* Data points */}
          {chartData.map((d, i) => (
            <circle
              key={i}
              cx={getX(d)}
              cy={getY(d)}
              r={4}
              fill={lineColor}
              stroke="white"
              strokeWidth={2}
            />
          ))}

          {/* X Axis */}
          <AxisBottom
            scale={xScale}
            top={innerHeight}
            hideTicks={true}
            tickFormat={formatTime}
            numTicks={Math.min(horizon, Math.max(5, Math.ceil(horizon / 4)))}
            tickLabelProps={() => ({
              fill: colors.axisTicks,
              fontSize: 10,
              textAnchor: "middle",
            })}
          />

          {/* Y Axis */}
          <AxisLeft
            scale={yScale}
            tickFormat={formatValue}
            numTicks={Math.min(4, Math.max(3, Math.ceil(yAxisMax / 2)))}
            hideTicks={true}
            tickLabelProps={() => ({
              fill: colors.axisTicks,
              fontSize: 10,
              textAnchor: "end",
              dx: "-0.25em",
              dy: "0.25em",
            })}
          />
        </Group>
      </svg>
    </div>
  );
}
