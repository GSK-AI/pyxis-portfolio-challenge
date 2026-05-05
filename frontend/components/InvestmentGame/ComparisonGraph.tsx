"use client";

import { useMemo } from "react";
import { scaleLinear } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { GridColumns, GridRows } from "@visx/grid";
import { ParentSize } from "@visx/responsive";
import { animated, useSpring } from "@react-spring/web";
import { format } from "@visx/vendor/d3-format";
import { formatDisplayNumber } from "@/lib/numbers";
import {
  getInnerDimensions,
  visualisationConsts,
} from "@/lib/visualisations/helpers";
import type { GameComparison } from "@/lib/definitionsGameZ";

const AnimatedLinePath = animated(LinePath);

interface DataPoint {
  time: number;
  value: number;
  agent: string;
}

interface ComparisonGraphProps {
  comparisonData: GameComparison;
  dataType?: "enpv_over_time" | "eroi_over_time";
}

interface ChartProps {
  width: number;
  height: number;
  comparisonData: GameComparison;
  dataType: "enpv_over_time" | "eroi_over_time";
}

function Chart({ width, height, comparisonData, dataType }: ChartProps) {
  const { colors } = visualisationConsts;
  const margin = {
    top: 20,
    right: 40,
    bottom: 40,
    left: 60,
  };
  const { innerWidth, innerHeight } = getInnerDimensions({
    width,
    height,
    margin,
  });

  // Process the data into line chart format based on dataType
  const processedData = useMemo(() => {
    const dataSource = comparisonData?.[dataType];
    if (!dataSource) return [];

    const agents = Object.keys(dataSource);
    return agents.map((agent) => {
      const timeSeriesData = dataSource[agent];
      return {
        agent,
        data: timeSeriesData.map((value, index) => ({
          time: index,
          value: dataType === "eroi_over_time" ? value : value / 1000000, // Don't convert EROI to millions
          agent,
        })),
      };
    });
  }, [comparisonData, dataType]); // Calculate domain ranges
  const timeRange = useMemo(() => {
    if (!processedData.length) return [0, 10];
    const maxTime = Math.max(
      ...processedData.map((series) => series.data.length - 1),
    );
    return [0, maxTime];
  }, [processedData]);

  const valueRange = useMemo(() => {
    if (!processedData.length) return [0, 100];
    const allValues = processedData.flatMap((series) =>
      series.data.map((d) => d.value),
    );
    const maxValue = Math.max(...allValues);
    const minValue = Math.min(...allValues);

    // Calculate appropriate range with some padding
    const range = maxValue - minValue;
    const padding = Math.max(range * 0.1, 0.1); // At least 0.1 million padding

    // Set Y min to the minimum value if it's negative, otherwise start from 0
    const yMin = minValue < 0 ? minValue - padding : 0;
    const yMax = maxValue + padding;

    return [yMin, yMax];
  }, [processedData]);

  // Calculate appropriate number of ticks based on data range
  const numYTicks = useMemo(() => {
    const range = valueRange[1] - valueRange[0];
    if (range <= 10) return 5;
    if (range <= 50) return Math.min(6, Math.max(4, Math.ceil(range / 10)));
    if (range <= 100) return Math.min(6, Math.max(4, Math.ceil(range / 20)));
    return Math.min(6, Math.max(4, Math.ceil(range / 50)));
  }, [valueRange]);

  // Create scales
  const xScale = scaleLinear({
    range: [margin.left, innerWidth + margin.left],
    domain: timeRange,
    nice: false,
  });

  const yScale = scaleLinear({
    range: [innerHeight + margin.top, margin.top],
    domain: valueRange,
    nice: true,
  });

  // Color function using visualisation constants
  const getLineColor = (agentIndex: number, total: number) => {
    if (agentIndex === 0) {
      // First agent (usually user) in teal
      return colors.plot; // "#1CA8C0" - teal
    }

    if (agentIndex === 1) {
      // Second agent uses original orange color
      return colors.plotHighlightSecondary; // "#fe7800" - orange
    }

    // Other agents (index > 1) in progressively darker orange variations
    const baseOrange = 0xfe7800; // #fe7800
    const darkeningFactor = 0.6; // Reduce brightness by 20% for each subsequent agent
    const adjustedBrightness = Math.pow(darkeningFactor, agentIndex - 1);

    const r = Math.floor(((baseOrange >> 16) & 0xff) * adjustedBrightness);
    const g = Math.floor(((baseOrange >> 8) & 0xff) * adjustedBrightness);
    const b = Math.floor((baseOrange & 0xff) * adjustedBrightness);

    return `rgb(${r}, ${g}, ${b})`;
  };

  // Animation spring
  const lineAnimation = useSpring({
    from: { opacity: 0 },
    to: { opacity: 1 },
    config: { duration: 800 },
  });

  // Format axis labels
  const formatTime = format("");
  const formatValue = (value: any) => {
    const numValue = Number(value);
    if (dataType === "eroi_over_time") {
      return formatDisplayNumber(numValue); // EROI values are already in correct units
    }
    return formatDisplayNumber(numValue * 1000000); // Convert back to actual value from millions for eNPV
  };

  if (!processedData.length) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="text-gray-500">No chart data available</div>
      </div>
    );
  }

  return (
    <svg width={width} height={height}>
      <Group>
        {/* Grid */}
        <GridRows
          left={margin.left}
          scale={yScale}
          width={innerWidth}
          stroke={colors.axisStroke}
          strokeWidth={1}
          numTicks={numYTicks}
        />
        <GridColumns
          top={margin.top}
          scale={xScale}
          height={innerHeight}
          stroke={colors.axisStroke}
          strokeWidth={1}
          numTicks={Math.min(
            timeRange[1] + 1,
            Math.max(5, Math.ceil(timeRange[1] / 4)),
          )}
        />

        {/* Lines */}
        {processedData.map((series, seriesIndex) => (
          <AnimatedLinePath
            key={series.agent}
            data={series.data}
            x={(d) => xScale((d as DataPoint).time)}
            y={(d) => yScale((d as DataPoint).value)}
            stroke={getLineColor(seriesIndex, processedData.length)}
            strokeWidth={2}
            strokeOpacity={0.8}
            curve={curveLinear}
            style={lineAnimation}
          />
        ))}

        {/* Y Axis */}
        <AxisLeft
          left={margin.left}
          scale={yScale}
          tickFormat={formatValue}
          numTicks={numYTicks}
          hideTicks={true}
          tickLabelProps={() => ({
            fill: colors.axisTicks,
            fontSize: 10,
            textAnchor: "end",
            dx: "-0.25em",
            dy: "0.25em",
          })}
        />
        <text x={margin.left} y="15" fontSize={10} fill={colors.axisTicks}>
          ({dataType === "enpv_over_time" ? "eNPV" : "eROI"})
        </text>

        {/* X Axis */}
        <AxisBottom
          top={innerHeight + margin.top}
          scale={xScale}
          hideTicks={true}
          tickFormat={formatTime}
          numTicks={Math.min(
            timeRange[1] + 1,
            Math.max(5, Math.ceil(timeRange[1] / 4)),
          )}
          tickLabelProps={() => ({
            fill: colors.axisTicks,
            fontSize: 10,
            textAnchor: "middle",
          })}
        />
      </Group>
    </svg>
  );
}

export default function ComparisonGraph({
  comparisonData,
  dataType = "enpv_over_time",
}: ComparisonGraphProps) {
  const dataSource = comparisonData?.[dataType];
  if (!dataSource || Object.keys(dataSource).length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="text-gray-500">No chart data available</div>
      </div>
    );
  }

  const title =
    dataType === "enpv_over_time" ? "eNPV over time" : "eROI over time";

  return (
    <div className="h-full w-full">
      <h3 className="mb-2 text-sm font-medium text-gray-700">{title}</h3>
      <div className="h-[calc(100%-2rem)] w-full">
        <ParentSize>
          {({ width, height }) => (
            <Chart
              width={width}
              height={height}
              comparisonData={comparisonData}
              dataType={dataType}
            />
          )}
        </ParentSize>
      </div>
    </div>
  );
}
