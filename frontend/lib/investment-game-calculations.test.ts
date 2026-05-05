import { describe, it, expect } from "vitest";
import {
  shouldIncludeAssetInCalculation,
  getIncludedAssets,
  calculateExpectedNPV,
  calculateExpectedROI,
  calculateAvailableCapital,
  calculateCapitalChange,
  hasCapitalChange,
  isInsufficientCapital,
  calculateEnpvChange,
  calculateEroiChange,
  hasEnpvChange,
  hasEroiChange,
} from "./investment-game-calculations";
import type { AssetSchemaType } from "./definitionsGameZ";

// Mock asset data for testing
const createMockAsset = (
  overrides: Partial<AssetSchemaType> = {},
): AssetSchemaType => ({
  id: "asset-1",
  name: "Test Asset",
  therapeutic_area: "oncology",
  type: "internal",
  description: "Test asset description",
  max_revenue: 1000000,
  time_until_max_revenue: 5,
  time_until_patent_expiry: 10,
  trials: {},
  state: "Idle",
  pending_trial_phase: null,
  time_on_market: 0,
  cost_this_step: 100000,
  revenue_this_step: 0,
  enpv: 500000,
  expected_costs: [100000, 150000, 200000],
  expected_revenues: [0, 0, 800000],
  eroi: 1.5,
  ...overrides,
});

describe("Investment Game Calculations", () => {
  describe("Asset inclusion logic", () => {
    describe("shouldIncludeAssetInCalculation", () => {
      it("should include In Development assets", () => {
        const asset = createMockAsset({ state: "In Development" });
        const selection = { "asset-1": false };

        const result = shouldIncludeAssetInCalculation(asset, selection);
        expect(result).toBe(true);
      });

      it("should include On Market assets", () => {
        const asset = createMockAsset({ state: "On Market" });
        const selection = { "asset-1": false };

        const result = shouldIncludeAssetInCalculation(asset, selection);
        expect(result).toBe(true);
      });

      it("should include selected Idle assets", () => {
        const asset = createMockAsset({ state: "Idle" });
        const selection = { "asset-1": true };

        const result = shouldIncludeAssetInCalculation(asset, selection);
        expect(result).toBe(true);
      });

      it("should exclude non-selected Idle assets", () => {
        const asset = createMockAsset({ state: "Idle" });
        const selection = { "asset-1": false };

        const result = shouldIncludeAssetInCalculation(asset, selection);
        expect(result).toBe(false);
      });

      it("should exclude Failed assets", () => {
        const asset = createMockAsset({ state: "Failed" });
        const selection = { "asset-1": true };

        const result = shouldIncludeAssetInCalculation(asset, selection);
        expect(result).toBe(false);
      });

      it("should exclude Expired assets", () => {
        const asset = createMockAsset({ state: "Expired" });
        const selection = { "asset-1": true };

        const result = shouldIncludeAssetInCalculation(asset, selection);
        expect(result).toBe(false);
      });
    });

    describe("getIncludedAssets", () => {
      it("should return only included assets", () => {
        const assets = [
          createMockAsset({ id: "asset-1", state: "In Development" }),
          createMockAsset({ id: "asset-2", state: "Idle" }),
          createMockAsset({ id: "asset-3", state: "Failed" }),
          createMockAsset({ id: "asset-4", state: "On Market" }),
        ];
        const selection = {
          "asset-1": false, // Should be included (In Development)
          "asset-2": true, // Should be included (Idle, selected)
          "asset-3": true, // Should not be included (Failed)
          "asset-4": false, // Should be included (On Market)
        };

        const result = getIncludedAssets(assets, selection);
        expect(result).toHaveLength(3);
        expect(result.map((a) => a.id)).toEqual([
          "asset-1",
          "asset-2",
          "asset-4",
        ]);
      });

      it("should return empty array when no assets are included", () => {
        const assets = [
          createMockAsset({ id: "asset-1", state: "Idle" }),
          createMockAsset({ id: "asset-2", state: "Failed" }),
        ];
        const selection = { "asset-1": false, "asset-2": true };

        const result = getIncludedAssets(assets, selection);
        expect(result).toHaveLength(0);
      });
    });
  });

  describe("Capital-related calculations", () => {
    describe("calculateAvailableCapital", () => {
      it("should calculate available capital correctly with next step cost", () => {
        const result = calculateAvailableCapital(1000000, 100000);
        expect(result).toBe(900000);
      });

      it("should handle undefined next step cost", () => {
        const result = calculateAvailableCapital(1000000);
        expect(result).toBe(1000000);
      });

      it("should handle zero next step cost", () => {
        const result = calculateAvailableCapital(1000000, 0);
        expect(result).toBe(1000000);
      });

      it("should handle negative available capital", () => {
        const result = calculateAvailableCapital(50000, 100000);
        expect(result).toBe(-50000);
      });
    });

    describe("calculateCapitalChange", () => {
      it("should calculate positive capital change", () => {
        const result = calculateCapitalChange(1200000, 1000000);
        expect(result).toBe(200000);
      });

      it("should calculate negative capital change", () => {
        const result = calculateCapitalChange(800000, 1000000);
        expect(result).toBe(-200000);
      });

      it("should return zero when no previous cash is provided", () => {
        const result = calculateCapitalChange(1000000);
        expect(result).toBe(0);
      });

      it("should handle zero capital change", () => {
        const result = calculateCapitalChange(1000000, 1000000);
        expect(result).toBe(0);
      });
    });

    describe("hasCapitalChange", () => {
      it("should return true when there is a capital change", () => {
        const result = hasCapitalChange(1000000, 200000);
        expect(result).toBe(true);
      });

      it("should return false when there is no capital change", () => {
        const result = hasCapitalChange(1000000, 0);
        expect(result).toBe(false);
      });

      it("should return false when previous cash is undefined", () => {
        const result = hasCapitalChange(undefined, 200000);
        expect(result).toBe(false);
      });

      it("should return false when capital change is undefined", () => {
        const result = hasCapitalChange(1000000);
        expect(result).toBe(false);
      });
    });

    describe("isInsufficientCapital", () => {
      it("should return true when capital is insufficient", () => {
        const result = isInsufficientCapital(50000, 100000);
        expect(result).toBe(true);
      });

      it("should return false when capital is sufficient", () => {
        const result = isInsufficientCapital(150000, 100000);
        expect(result).toBe(false);
      });

      it("should return false when capital exactly matches cost", () => {
        const result = isInsufficientCapital(100000, 100000);
        expect(result).toBe(false);
      });

      it("should return false when no next step cost is provided", () => {
        const result = isInsufficientCapital(100000);
        expect(result).toBe(false);
      });
    });
  });

  describe("Expected NPV calculations", () => {
    describe("calculateExpectedNPV", () => {
      it("should include In Development assets in NPV calculation", () => {
        const assets = [
          createMockAsset({ state: "In Development", enpv: 500000 }),
          createMockAsset({ id: "asset-2", state: "Idle", enpv: 300000 }),
        ];
        const selection = { "asset-1": false, "asset-2": false };

        const result = calculateExpectedNPV(assets, selection);
        expect(result).toBe(500000);
      });

      it("should include On Market assets in NPV calculation", () => {
        const assets = [
          createMockAsset({ state: "On Market", enpv: 700000 }),
          createMockAsset({ id: "asset-2", state: "Idle", enpv: 300000 }),
        ];
        const selection = { "asset-1": false, "asset-2": false };

        const result = calculateExpectedNPV(assets, selection);
        expect(result).toBe(700000);
      });

      it("should include selected Idle assets in NPV calculation", () => {
        const assets = [
          createMockAsset({ state: "Idle", enpv: 400000 }),
          createMockAsset({ id: "asset-2", state: "Idle", enpv: 300000 }),
        ];
        const selection = { "asset-1": true, "asset-2": false };

        const result = calculateExpectedNPV(assets, selection);
        expect(result).toBe(400000);
      });

      it("should exclude non-selected Idle assets from NPV calculation", () => {
        const assets = [createMockAsset({ state: "Idle", enpv: 400000 })];
        const selection = { "asset-1": false };

        const result = calculateExpectedNPV(assets, selection);
        expect(result).toBe(0);
      });

      it("should exclude Failed and Expired assets from NPV calculation", () => {
        const assets = [
          createMockAsset({ state: "Failed", enpv: 400000 }),
          createMockAsset({ id: "asset-2", state: "Expired", enpv: 300000 }),
        ];
        const selection = { "asset-1": true, "asset-2": true };

        const result = calculateExpectedNPV(assets, selection);
        expect(result).toBe(0);
      });

      it("should handle mixed asset states correctly", () => {
        const assets = [
          createMockAsset({
            id: "asset-1",
            state: "In Development",
            enpv: 500000,
          }),
          createMockAsset({ id: "asset-2", state: "On Market", enpv: 700000 }),
          createMockAsset({ id: "asset-3", state: "Idle", enpv: 300000 }),
          createMockAsset({ id: "asset-4", state: "Idle", enpv: 200000 }),
          createMockAsset({ id: "asset-5", state: "Failed", enpv: 100000 }),
        ];
        const selection = {
          "asset-1": false, // Should be included (In Development)
          "asset-2": false, // Should be included (On Market)
          "asset-3": true, // Should be included (Idle, selected)
          "asset-4": false, // Should not be included (Idle, not selected)
          "asset-5": true, // Should not be included (Failed)
        };

        const result = calculateExpectedNPV(assets, selection);
        expect(result).toBe(1500000); // 500000 + 700000 + 300000
      });
    });

    describe("calculateEnpvChange", () => {
      it("should calculate positive eNPV change", () => {
        const currentNPV = 1000000;
        const previousAssets = [
          createMockAsset({ state: "In Development", enpv: 400000 }),
        ];
        const selection = { "asset-1": false };

        const result = calculateEnpvChange(
          currentNPV,
          previousAssets,
          selection,
        );
        expect(result).toBe(600000); // 1000000 - 400000
      });

      it("should calculate negative eNPV change", () => {
        const currentNPV = 300000;
        const previousAssets = [
          createMockAsset({ state: "In Development", enpv: 500000 }),
        ];
        const selection = { "asset-1": false };

        const result = calculateEnpvChange(
          currentNPV,
          previousAssets,
          selection,
        );
        expect(result).toBe(-200000); // 300000 - 500000
      });

      it("should return zero when no previous assets", () => {
        const result = calculateEnpvChange(1000000);
        expect(result).toBe(0);
      });

      it("should return zero when no selection provided", () => {
        const previousAssets = [createMockAsset()];
        const result = calculateEnpvChange(1000000, previousAssets);
        expect(result).toBe(0);
      });
    });

    describe("hasEnpvChange", () => {
      it("should return true when there is an eNPV change and time > 0", () => {
        const result = hasEnpvChange(1, 100000, [createMockAsset()]);
        expect(result).toBe(true);
      });

      it("should return false when time is 0", () => {
        const result = hasEnpvChange(0, 100000, [createMockAsset()]);
        expect(result).toBe(false);
      });

      it("should return false when eNPV change is 0", () => {
        const result = hasEnpvChange(1, 0, [createMockAsset()]);
        expect(result).toBe(false);
      });

      it("should return false when no previous assets", () => {
        const result = hasEnpvChange(1, 100000);
        expect(result).toBe(false);
      });
    });
  });

  describe("Expected ROI calculations", () => {
    describe("calculateExpectedROI", () => {
      it("should calculate ROI correctly for In Development assets", () => {
        const assets = [
          createMockAsset({
            state: "In Development",
            expected_revenues: [0, 0, 1000000],
            expected_costs: [100000, 200000, 100000],
          }),
        ];
        const selection = { "asset-1": false };

        const result = calculateExpectedROI(assets, selection);
        // Total revenues: 1000000, Total costs: 400000
        // ROI = (1000000 - 400000) / 400000 = 1.5
        expect(result).toBe(1.5);
      });

      it("should return 0 when total expected costs is 0", () => {
        const assets = [
          createMockAsset({
            state: "In Development",
            expected_revenues: [1000000],
            expected_costs: [0],
          }),
        ];
        const selection = { "asset-1": false };

        const result = calculateExpectedROI(assets, selection);
        expect(result).toBe(0);
      });

      it("should include only selected Idle assets in ROI calculation", () => {
        const assets = [
          createMockAsset({
            id: "asset-1",
            state: "Idle",
            expected_revenues: [500000],
            expected_costs: [200000],
          }),
          createMockAsset({
            id: "asset-2",
            state: "Idle",
            expected_revenues: [300000],
            expected_costs: [100000],
          }),
        ];
        const selection = { "asset-1": true, "asset-2": false };

        const result = calculateExpectedROI(assets, selection);
        // Only asset-1: revenues: 500000, costs: 200000
        // ROI = (500000 - 200000) / 200000 = 1.5
        expect(result).toBe(1.5);
      });

      it("should handle mixed asset states in ROI calculation", () => {
        const assets = [
          createMockAsset({
            id: "asset-1",
            state: "In Development",
            expected_revenues: [0, 600000],
            expected_costs: [100000, 100000],
          }),
          createMockAsset({
            id: "asset-2",
            state: "On Market",
            expected_revenues: [400000],
            expected_costs: [100000],
          }),
          createMockAsset({
            id: "asset-3",
            state: "Idle",
            expected_revenues: [200000],
            expected_costs: [50000],
          }),
        ];
        const selection = {
          "asset-1": false, // Included (In Development)
          "asset-2": false, // Included (On Market)
          "asset-3": true, // Included (Idle, selected)
        };

        const result = calculateExpectedROI(assets, selection);
        // Total revenues: 600000 + 400000 + 200000 = 1200000
        // Total costs: 200000 + 100000 + 50000 = 350000
        // ROI = (1200000 - 350000) / 350000 = 2.428...
        expect(result).toBeCloseTo(2.428, 2);
      });
    });

    describe("calculateEroiChange", () => {
      it("should calculate positive eROI change", () => {
        const currentROI = 2.5;
        const previousAssets = [
          createMockAsset({
            state: "In Development",
            expected_revenues: [600000],
            expected_costs: [300000],
          }),
        ];
        const selection = { "asset-1": false };

        const result = calculateEroiChange(
          currentROI,
          previousAssets,
          selection,
        );
        // Previous ROI = (600000 - 300000) / 300000 = 1.0
        // Change = 2.5 - 1.0 = 1.5
        expect(result).toBe(1.5);
      });

      it("should return zero when no previous assets", () => {
        const result = calculateEroiChange(2.5);
        expect(result).toBe(0);
      });

      it("should return zero when no selection provided", () => {
        const previousAssets = [createMockAsset()];
        const result = calculateEroiChange(2.5, previousAssets);
        expect(result).toBe(0);
      });
    });

    describe("hasEroiChange", () => {
      it("should return true when there is an eROI change and time > 0", () => {
        const result = hasEroiChange(1, 0.5, [createMockAsset()]);
        expect(result).toBe(true);
      });

      it("should return false when time is 0", () => {
        const result = hasEroiChange(0, 0.5, [createMockAsset()]);
        expect(result).toBe(false);
      });

      it("should return false when eROI change is 0", () => {
        const result = hasEroiChange(1, 0, [createMockAsset()]);
        expect(result).toBe(false);
      });

      it("should return false when no previous assets", () => {
        const result = hasEroiChange(1, 0.5);
        expect(result).toBe(false);
      });
    });
  });

  describe("Edge cases and error handling", () => {
    it("should handle empty assets array", () => {
      const assets: AssetSchemaType[] = [];
      const selection = {};

      const npv = calculateExpectedNPV(assets, selection);
      const roi = calculateExpectedROI(assets, selection);

      expect(npv).toBe(0);
      expect(roi).toBe(0);
    });

    it("should handle assets with null/undefined expected values", () => {
      const assets = [
        createMockAsset({
          state: "In Development",
          expected_revenues: undefined as any,
          expected_costs: undefined as any,
        }),
      ];
      const selection = { "asset-1": false };

      const roi = calculateExpectedROI(assets, selection);
      expect(roi).toBe(0);
    });

    it("should handle very large numbers", () => {
      const assets = [
        createMockAsset({
          state: "In Development",
          enpv: 1e12, // 1 trillion
          expected_revenues: [1e12],
          expected_costs: [5e11], // 500 billion
        }),
      ];
      const selection = { "asset-1": false };

      const npv = calculateExpectedNPV(assets, selection);
      const roi = calculateExpectedROI(assets, selection);

      expect(npv).toBe(1e12);
      expect(roi).toBe(1); // (1e12 - 5e11) / 5e11 = 1
    });

    it("should handle negative eNPV values", () => {
      const assets = [
        createMockAsset({
          state: "In Development",
          enpv: -500000,
        }),
      ];
      const selection = { "asset-1": false };

      const npv = calculateExpectedNPV(assets, selection);
      expect(npv).toBe(-500000);
    });
  });
});
