import { scaleLinear } from "@visx/scale";
import { Point } from "@visx/point";

export const visualisationConsts = {
  margin: { top: 40, left: 80, right: 80, bottom: 80 },
  colors: {
    webStroke: "#e0e0e0",
    axisStroke: "#e0e0e0",
    plot: "#1CA8C0",
    plotHighlight: "#1CA8C0",
    plotHighlightSecondary: "#fe7800",
    axisTicks: "#888888",
    dark: "#202020",
    darkLight: "#505050",
  },
} as const;

export function colorGetter(idx: number) {
  const defaultColor = visualisationConsts.colors.plotHighlight;
  const colorArr = [
    visualisationConsts.colors.plotHighlight,
    visualisationConsts.colors.plotHighlightSecondary,
  ];
  if (idx > colorArr.length - 1) {
    return defaultColor;
  }
  return colorArr[idx];
}

export function getRadialScale(degrees: number) {
  return scaleLinear<number>({
    range: [0, Math.PI * 2],
    domain: [degrees, 0],
  });
}

export function getDimensionMax(params: {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
}) {
  const { width, height, margin } = params;
  const xMax = width - margin.left - margin.right;
  const yMax = height - margin.top - margin.bottom;

  return { xMax, yMax };
}

export function getInnerDimensions(params: {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
}) {
  const { width, height, margin } = params;
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  return { innerWidth, innerHeight };
}

export const zeroPoint = new Point({ x: 0, y: 0 });
