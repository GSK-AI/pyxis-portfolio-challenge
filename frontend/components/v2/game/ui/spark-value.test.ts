import { describe, expect, it } from "vitest";

import { sparkValuePlacement } from "./SparkValue";

/**
 * The compact (sparkline) charts have no axes, so the dot label is the only
 * number on the plot — it must never be clipped by the svg edges.
 */

describe("sparkValuePlacement", () => {
  it("sits to the right of the dot when there is room", () => {
    const placed = sparkValuePlacement({
      x: 20,
      y: 30,
      width: 240,
      label: "£1.2B",
    });
    expect(placed.textAnchor).toBe("start");
    expect(placed.x).toBeGreaterThan(20);
    expect(placed.y).toBe(24);
  });

  it("flips to the left of the dot near the right edge", () => {
    const placed = sparkValuePlacement({
      x: 230,
      y: 30,
      width: 240,
      label: "£1.2B",
    });
    expect(placed.textAnchor).toBe("end");
    expect(placed.x).toBeLessThan(230);
  });

  it("flips earlier for a longer label", () => {
    const at = (label: string) =>
      sparkValuePlacement({ x: 195, y: 30, width: 240, label }).textAnchor;
    expect(at("£0")).toBe("start");
    expect(at("£123.4M")).toBe("end");
  });

  it("clamps a dot at the top of the plot so the glyphs stay inside", () => {
    const placed = sparkValuePlacement({
      x: 20,
      y: 2,
      width: 240,
      label: "£1.2B",
    });
    expect(placed.y).toBe(10);
  });
});
