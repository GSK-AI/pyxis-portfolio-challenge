import { describe, expect, it } from "vitest";
import steps from "./gameOnboarding";

const byName = (tour: string) => steps.find((t) => t.tour === tour);

describe("tour registry", () => {
  it("has unique tour names", () => {
    const names = steps.map((t) => t.tour);
    expect(new Set(names).size).toBe(names.length);
  });

  it("gives every step some content", () => {
    for (const tour of steps) {
      for (const [index, step] of tour.steps.entries()) {
        // Titles are optional — a couple of the older screens deliberately
        // render a card with body copy only.
        expect(step.content, `${tour.tour}[${index}] content`).toBeTruthy();
      }
    }
  });
});

describe("v2 game tours", () => {
  const multi = byName("gameV2Multi");
  const single = byName("gameV2Single");

  it("registers a tour per mode", () => {
    expect(multi).toBeDefined();
    expect(single).toBeDefined();
  });

  it("titles every v2 step", () => {
    for (const tour of [multi!, single!]) {
      tour.steps.forEach((step, index) => {
        expect(step.title, `${tour.tour}[${index}]`).toBeTruthy();
      });
    }
  });

  // Every anchor has to exist in both the full dashboard and focus view, so
  // the tour never has to move the player between layouts mid-run. Adding a
  // selector here means adding an id in the v2 game components.
  const anchors = [
    "#v2-tour-stats",
    "#v2-tour-charts",
    "#v2-tour-table",
    "#v2-tour-row",
    "#v2-tour-tabs",
    "#v2-tour-rail",
    "#v2-tour-focus",
    "#v2-tour-controls",
  ];

  it.each([
    ["gameV2Multi", multi],
    ["gameV2Single", single],
  ])("%s covers every anchor exactly once", (_name, tour) => {
    const selectors = tour!.steps.map((s) => s.selector).filter(Boolean);
    for (const anchor of anchors) {
      expect(selectors.filter((s) => s === anchor)).toHaveLength(1);
    }
  });

  it("opens and closes on a centred, selector-less card", () => {
    for (const tour of [multi!, single!]) {
      expect(tour.steps[0].selector).toBeUndefined();
      expect(tour.steps[tour.steps.length - 1].selector).toBeUndefined();
    }
  });

  it("only offers the leaderboard step in multiplayer", () => {
    expect(multi!.steps.map((s) => s.selector)).toContain(
      "#v2-tour-leaderboard",
    );
    expect(single!.steps.map((s) => s.selector)).not.toContain(
      "#v2-tour-leaderboard",
    );
  });

  // nextstep positions the card outside the element and the overlay clips
  // whatever runs past the viewport edge, so anchors near the right edge
  // have to throw the card inward and anchored copy has to stay short
  // enough that the card doesn't outgrow the space beside its target.
  const rightEdgeAnchors = [
    "#v2-tour-rail",
    "#v2-tour-leaderboard",
    "#v2-tour-controls",
  ];

  it("keeps right-edge cards pointing inward", () => {
    for (const tour of [multi!, single!]) {
      for (const step of tour.steps) {
        if (!rightEdgeAnchors.includes(step.selector ?? "")) continue;
        expect(step.side, `${tour.tour} ${step.selector}`).toMatch(
          /^(left|bottom-right|top-right)$/,
        );
      }
    }
  });

  it("keeps anchored copy short enough to fit beside its target", () => {
    for (const tour of [multi!, single!]) {
      for (const step of tour.steps) {
        // Selector-less steps render a centred card — length is free there.
        if (!step.selector) continue;
        expect(
          String(step.content).length,
          `${tour.tour} ${step.selector}`,
        ).toBeLessThanOrEqual(260);
      }
    }
  });

  // Anchors are sized to what they describe, so the spotlight should sit on
  // them rather than float around them — nextstep's 30px-a-side default is
  // loose enough to read as a box of empty space, and on the table anchors
  // (which already span the frame) it spills past the edge.
  it("hugs the spotlight on every step", () => {
    for (const tour of [multi!, single!]) {
      for (const [index, step] of tour.steps.entries()) {
        expect(
          step.pointerPadding,
          `${tour.tour}[${index}] ${step.selector ?? "centred"}`,
        ).toBeLessThanOrEqual(8);
      }
    }
  });

  it("lets the player skip from anywhere but the last step", () => {
    for (const tour of [multi!, single!]) {
      const last = tour.steps.length - 1;
      tour.steps.forEach((step, index) => {
        expect(step.showSkip, `${tour.tour}[${index}]`).toBe(index !== last);
      });
    }
  });
});
