"use client";

import { useMemo } from "react";
import { scaleLinear } from "@visx/scale";
import { AreaClosed, Circle } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { Group } from "@visx/group";
import { format } from "@visx/vendor/d3-format";
import { animated, useSpring } from "@react-spring/web";

import type {
  AssetSchemaType,
  GameStepSchemaType,
  DataType,
  ActionType,
} from "@/lib/definitionsGameZ";
import {
  visualisationConsts,
  getInnerDimensions,
} from "@/lib/visualisations/helpers";
import { GridColumns, GridRows } from "@visx/grid";
import { formatDisplayNumber } from "@/lib/numbers";
import {
  calculateChartYAxisMax,
  processAssetDataForChart,
} from "@/lib/game-data";
import { InformationButton } from "../InformationButton";
import { informationDictionary } from "@/lib/information-dictionary-game";

const AnimatedAreaClosed = animated(AreaClosed);
const AnimatedCircle = animated(Circle);

interface DataPoint {
  time: number;
  value: number;
  assetId: string;
  assetName: string;
  isSelected?: ActionType | boolean;
}

interface StackedDataPoint {
  time: number;
  y0: number;
  y1: number;
  value: number;
  assetIndex: number;
  assetId: string;
  assetName: string;
}

export default function ActionChart({
  assets,
  selection,
  horizon,
  currentTime,
  gameState,
  dataType = "cost",
  showGrid = false,
  height = 200,
  width = 500,
  margin = { top: 40, right: 30, bottom: 40, left: 60 },
  chartTitle,
  hintCosts = 0,
  infoLabel,
}: {
  assets: AssetSchemaType[];
  selection: Record<string, ActionType | boolean>;
  horizon: number;
  currentTime?: number;
  gameState?: GameStepSchemaType;
  dataType?: DataType;
  showGrid?: boolean;
  height?: number;
  width?: number;
  margin?: { top: number; right: number; bottom: number; left: number };
  chartTitle?: string;
  hintCosts?: number;
  infoLabel?: string;
}) {
  const { colors } = visualisationConsts;
  const { innerWidth, innerHeight } = getInnerDimensions({
    width,
    height,
    margin,
  });

  const processedData = useMemo(() => {
    try {
      return processAssetDataForChart({
        assets,
        selection,
        horizon,
        dataType,
        currentTime,
        gameState,
        hintCosts,
      });
    } catch (error) {
      console.error("[ActionChart] Error processing data:", error);
      return [];
    }
  }, [assets, selection, horizon, dataType, currentTime, gameState, hintCosts]);

  const xScale = scaleLinear({
    range: [margin.left, innerWidth + margin.left],
    domain: [0, horizon],
    nice: false,
  });

  const stackedData = useMemo(() => {
    try {
      const timePoints = Array.from({ length: horizon + 1 }, (_, i) => i);

      const stacked = timePoints.map((time) => {
        let cumulativeValue = 0;
        const layers = processedData.map((assetSeries, assetIndex) => {
          const dataPoint = assetSeries.find((d) => d.time === time);
          const value = (dataPoint?.value || 0) / 1000000; // Convert to millions
          const y0 = cumulativeValue;
          cumulativeValue += value;
          return {
            time,
            y0,
            y1: cumulativeValue,
            value,
            assetIndex,
            assetId: dataPoint?.assetId || "",
            assetName: dataPoint?.assetName || "",
          };
        });
        return layers;
      });

      return stacked;
    } catch (error) {
      console.error("[ActionChart] Error creating stacked data:", error);
      return [];
    }
  }, [
    processedData,
    horizon,
    gameState,
    dataType,
    currentTime,
    assets,
    selection,
  ]);

  const yAxisMax = useMemo(() => {
    try {
      const maxValue = calculateChartYAxisMax({
        assets,
        horizon,
        dataType,
        currentTime,
        gameState,
        bufferPercentage: 0.2,
        minDomain: 10,
      });

      return maxValue;
    } catch (error) {
      console.error("[ActionChart] Error calculating y-axis max:", error);
      return 10; // Fallback value
    }
  }, [
    assets,
    horizon,
    dataType,
    currentTime,
    gameState,
    processedData,
    stackedData,
    selection,
  ]);

  const yScale = scaleLinear({
    range: [innerHeight + margin.top, margin.top],
    domain: [0, yAxisMax],
    nice: false,
  });

  const formatTime = format("");
  const formatValue = (value: any) => {
    const numValue = Number(value);
    return formatDisplayNumber(numValue * 1000000); // Convert back to actual value from millions
  };

  // Color function - blue up to current time, lighter blue beyond
  const getAssetColor = (
    assetSeries: DataPoint[],
    index: number,
    total: number,
    timePoint?: number,
  ) => {
    const isSelected = assetSeries[0]?.isSelected || false;

    const useBlueForTime =
      timePoint !== undefined &&
      currentTime !== undefined &&
      timePoint <= currentTime;

    if (isSelected || useBlueForTime) {
      if (useBlueForTime) {
        return "rgb(37 137 254)"; // Blue for realized data
      }
      const baseHue = 173; // Changed from 173 (teal) to 210 (blue)
      const saturation = 81;
      const lightness = 40 - (index / Math.max(total - 1, 1)) * 5;
      return `hsl(${baseHue}, ${saturation}%, ${lightness}%)`;
    } else {
      // Lighter blue shades for always included assets beyond current time
      const baseHue = 200;
      const saturation = 60;
      const lightness = 75 - (index / Math.max(total - 1, 1)) * 20;
      return `hsl(${baseHue}, ${saturation}%, ${lightness}%)`;
    }
  };

  const getStrokeWidth = (assetSeries: DataPoint[], timePoint?: number) => {
    // No strokes for realised data (up to currentTime)
    const isRealisedTime =
      timePoint !== undefined &&
      currentTime !== undefined &&
      timePoint <= currentTime;

    if (isRealisedTime) {
      return 0; // No stroke for realised data
    }

    const isSelected = assetSeries[0]?.isSelected || false;
    return isSelected ? 1 : 0; // Stroke only for selected assets in future periods
  };

  const getStrokeDashArray = (assetSeries: DataPoint[]) => {
    const isSelected = assetSeries[0]?.isSelected || false;
    return isSelected ? "none" : "none";
  };

  // Animation spring for smooth transitions
  const areaAnimation = useSpring({
    from: { opacity: 0 },
    to: { opacity: 0.7 },
    config: { duration: 800 },
  });

  // Split stacked data into past/current (blue) and future (lighter blue) segments
  const { pastData, futureData } = useMemo(() => {
    if (currentTime === undefined) {
      return { pastData: stackedData, futureData: [] };
    }

    const splitIndex = currentTime + 1; // Include current time in past data
    const pastData = stackedData.slice(0, splitIndex);
    const futureData = stackedData.slice(splitIndex - 1); // Overlap at current time for continuity

    return { pastData, futureData };
  }, [stackedData, currentTime]);

  // Calculate total value at next time for display in title
  const totalValueAtNextTime = useMemo(() => {
    if (currentTime === undefined || currentTime >= horizon) return null;

    const nextTime = currentTime + 1;
    const nextTimeData = stackedData.find(
      (timeData) => timeData[0]?.time === nextTime,
    );
    if (!nextTimeData) return null;

    // Find the topmost asset (last in the array that has data at next time)
    let topPoint: StackedDataPoint | null = null;

    for (let i = processedData.length - 1; i >= 0; i--) {
      const point = nextTimeData[i] as StackedDataPoint;

      // Show indicator for any valid data point, including zero values
      if (point !== undefined && point !== null) {
        topPoint = point;
        break;
      }
    }

    // If no asset data, still show indicator at zero level if we have time data
    if (!topPoint && nextTimeData.length > 0) {
      topPoint = {
        time: nextTime,
        y0: 0,
        y1: 0,
        value: 0,
        assetIndex: 0,
        assetId: "",
        assetName: "No assets",
      };
    }

    return topPoint ? topPoint.y1 * 1000000 : null; // Convert back to actual value
  }, [stackedData, currentTime, horizon, processedData]);

  return (
    <div className="relative rounded-lg bg-gray-50 p-2">
      {chartTitle && (
        <h3 className="flex items-center gap-0 font-light text-gray-600">
          {chartTitle}
          <span className="ml-2">
            {totalValueAtNextTime === null || totalValueAtNextTime === 0
              ? "£0"
              : `£${formatDisplayNumber(totalValueAtNextTime)}`}
          </span>
          {infoLabel && infoLabel in informationDictionary && (
            <div className="ml-2 flex items-center">
              <InformationButton
                title={
                  informationDictionary[
                    infoLabel as keyof typeof informationDictionary
                  ].title
                }
                description={
                  informationDictionary[
                    infoLabel as keyof typeof informationDictionary
                  ].description
                }
                buttonClassName="w-4 h-4"
              />
            </div>
          )}
        </h3>
      )}
      <svg width={width} height={height}>
        <Group>
          {/* Grid Lines (Optional) */}
          {showGrid && (
            <>
              {/* Y-axis Grid Lines (Horizontal) */}
              <GridRows
                left={margin.left}
                scale={yScale}
                width={innerWidth}
                stroke={colors.axisStroke}
                strokeDasharray="4,4"
                numTicks={5}
              />

              {/* X-axis Grid Lines (Vertical) */}
              <GridColumns
                top={margin.top}
                scale={xScale}
                height={innerHeight}
                stroke={colors.axisStroke}
                strokeDasharray="4,4"
                numTicks={Math.min(
                  horizon,
                  Math.max(5, Math.ceil(horizon / 4)),
                )} // Match X-axis ticks
              />
            </>
          )}

          {/* X Axis */}
          <AxisBottom
            top={innerHeight + margin.top}
            scale={xScale}
            hideTicks={true}
            tickFormat={formatTime}
            numTicks={Math.min(horizon, Math.max(5, Math.ceil(horizon / 4)))} // Limit ticks to prevent overlap
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
          <text x={margin.left} y="15" fontSize={12} fill={colors.axisTicks}>
            ({dataType === "cost" ? "Expected Cost" : "Expected Budget"})
          </text>

          {/* Stacked Area Charts - Past/Current (Blue) */}
          {processedData.map((assetSeries, assetIndex) => (
            <Group key={`past-${assetSeries[0]?.assetId || assetIndex}`}>
              {pastData.length > 0 && (
                <AnimatedAreaClosed
                  data={pastData
                    .map((timeData) => timeData[assetIndex])
                    .filter(Boolean)}
                  x={(d) => xScale((d as StackedDataPoint).time) ?? 0}
                  y={(d) => yScale((d as StackedDataPoint).y1) ?? 0}
                  y0={(d) => yScale((d as StackedDataPoint).y0) ?? 0}
                  yScale={yScale}
                  curve={curveLinear}
                  fill={getAssetColor(
                    assetSeries,
                    assetIndex,
                    processedData.length,
                    0,
                  )} // Force blue
                  stroke={getAssetColor(
                    assetSeries,
                    assetIndex,
                    processedData.length,
                    0,
                  )}
                  strokeWidth={getStrokeWidth(assetSeries, 0)}
                  strokeDasharray={getStrokeDashArray(assetSeries)}
                  style={{ opacity: areaAnimation.opacity }}
                />
              )}
            </Group>
          ))}

          {/* Stacked Area Charts - Future (Blue) */}
          {processedData.map((assetSeries, assetIndex) => (
            <Group key={`future-${assetSeries[0]?.assetId || assetIndex}`}>
              {futureData.length > 0 && (
                <AnimatedAreaClosed
                  data={futureData
                    .map((timeData) => timeData[assetIndex])
                    .filter(Boolean)}
                  x={(d) => xScale((d as StackedDataPoint).time) ?? 0}
                  y={(d) => yScale((d as StackedDataPoint).y1) ?? 0}
                  y0={(d) => yScale((d as StackedDataPoint).y0) ?? 0}
                  yScale={yScale}
                  curve={curveLinear}
                  fill={getAssetColor(
                    assetSeries,
                    assetIndex,
                    processedData.length,
                    999,
                  )} // Force blue
                  stroke={getAssetColor(
                    assetSeries,
                    assetIndex,
                    processedData.length,
                    999,
                  )}
                  strokeWidth={getStrokeWidth(assetSeries, 999)}
                  strokeDasharray={getStrokeDashArray(assetSeries)}
                  style={{ opacity: areaAnimation.opacity }}
                />
              )}
            </Group>
          ))}

          {/* Dots for current position */}
          {currentTime !== undefined &&
            (() => {
              // Find the point at current time
              const currentTimeData = stackedData.find(
                (timeData) => timeData[0]?.time === currentTime,
              );
              if (!currentTimeData || currentTimeData.length === 0) return null;

              // Get the topmost point (last in array with highest y1 value)
              const topPoint = currentTimeData[
                currentTimeData.length - 1
              ] as StackedDataPoint;
              if (!topPoint) return null;

              return (
                <AnimatedCircle
                  key="current-time-dot"
                  cx={xScale(topPoint.time)}
                  cy={yScale(topPoint.y1)}
                  r={6}
                  fill="rgb(37 137 254 / var(--tw-ring-opacity, 1))" // Changed from teal to blue
                  stroke="white"
                  strokeWidth={2}
                  style={{ opacity: areaAnimation.opacity }}
                />
              );
            })()}

          {/* Next Step Indicator */}
          {(() => {
            if (currentTime === undefined || currentTime >= horizon)
              return null;

            const nextTime = currentTime + 1;
            const nextTimeData = stackedData.find(
              (timeData) => timeData[0]?.time === nextTime,
            );
            if (!nextTimeData) return null;

            // Find the topmost asset (last in the array that has data at next time)
            let topAssetIndex = -1;
            let topPoint: StackedDataPoint | null = null;

            for (let i = processedData.length - 1; i >= 0; i--) {
              const point = nextTimeData[i] as StackedDataPoint;

              // Show indicator for any valid data point, including zero values
              if (point !== undefined && point !== null) {
                topAssetIndex = i;
                topPoint = point;
                break;
              }
            }

            // Always show the indicator if we have any data point, even if the stack height is zero
            if (!topPoint || topAssetIndex === -1) {
              // If no asset data, still show indicator at zero level if we have time data
              if (nextTimeData.length > 0) {
                topPoint = {
                  time: nextTime,
                  y0: 0,
                  y1: 0,
                  value: 0,
                  assetIndex: 0,
                  assetId: "",
                  assetName: "No assets",
                };
                topAssetIndex = 0;
              } else {
                return null;
              }
            }

            const nextX = xScale(nextTime);
            const nextY = yScale(topPoint.y1);
            const totalValueAtNextTime = topPoint.y1 * 1000000; // Convert back to actual value

            // Position for the label at 45 degrees above the circle
            const distance = 50; // Distance from circle center to label
            const angle = -135 * (Math.PI / 180); // -135 degrees (up and to the left)
            const labelX = nextX + distance * Math.cos(angle);
            const labelY = nextY + distance * Math.sin(angle);

            return (
              <Group key="next-step-indicator">
                {/* Next step circle */}
                <Circle
                  cx={nextX}
                  cy={nextY}
                  r={4}
                  fill={colors.plot}
                  strokeWidth={1}
                  strokeDasharray="4,2"
                />

                {/* Pointing line */}
                <line
                  x1={nextX - 3}
                  y1={nextY - 3}
                  x2={labelX + 25}
                  y2={labelY + 10}
                  stroke={colors.plot}
                />

                {/* Value label text - single line */}
                {(() => {
                  const formattedValue =
                    totalValueAtNextTime === 0
                      ? `£0`
                      : `£${formatDisplayNumber(totalValueAtNextTime)}`;
                  // Estimate text width: roughly 6.5 pixels per character for fontSize 11
                  const textWidth = formattedValue.length * 6.5;
                  const padding = 8; // 4px padding on each side
                  const rectWidth = Math.max(textWidth + padding, 50); // Minimum width of 50px

                  return (
                    <>
                      <rect
                        x={labelX - rectWidth / 2}
                        y={labelY - 8}
                        width={rectWidth}
                        height={16}
                        rx={4}
                        fill="white"
                        stroke={colors.plot}
                        strokeWidth={1}
                        opacity={0.9}
                      />
                      <text
                        x={labelX}
                        y={labelY + 4}
                        textAnchor="middle"
                        fontSize={11}
                        fill={colors.plot}
                        fontWeight="600"
                      >
                        {formattedValue}
                      </text>
                    </>
                  );
                })()}
              </Group>
            );
          })()}
        </Group>
      </svg>
    </div>
  );
}
