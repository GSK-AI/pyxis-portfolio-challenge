import type { AssetSchemaType, ActionType } from "./definitionsGameZ";

/**
 * Helper to check if a selection value means "selected for investment"
 */
export function isSelectionActive(
  val: ActionType | boolean | undefined,
): boolean {
  if (val === true) return true;
  if (typeof val === "string" && val !== "none" && val !== "stop") return true;
  return false;
}

/**
 * Determines if an asset should be included in calculations
 * Rules: In Development (always, unless "stop" selected), On Market (always), Idle (if selected)
 */
export function shouldIncludeAssetInCalculation(
  asset: AssetSchemaType,
  selection: Record<string, ActionType | boolean>,
): boolean {
  const selVal = selection[asset.id];

  // On Market assets are always included
  if (asset.state === "On Market") return true;

  // In Development assets are included unless "stop" is selected
  if (asset.state === "In Development") {
    return selVal !== "stop";
  }

  // Idle assets are included if selected
  if (asset.state === "Idle") {
    return isSelectionActive(selVal);
  }

  return false;
}

/**
 * Get all assets that should be included in calculations
 */
export function getIncludedAssets(
  assets: AssetSchemaType[],
  selection: Record<string, ActionType | boolean>,
): AssetSchemaType[] {
  return assets.filter((asset) =>
    shouldIncludeAssetInCalculation(asset, selection),
  );
}

/**
 * Calculate expected NPV for all relevant assets
 * Includes NPV from: In Development (always), Idle (if selected), On Market (always)
 */
export function calculateExpectedNPV(
  assets: AssetSchemaType[],
  selection: Record<string, ActionType | boolean>,
): number {
  return getIncludedAssets(assets, selection).reduce(
    (total, asset) => total + asset.enpv,
    0,
  );
}

/**
 * Calculate expected ROI for all relevant assets
 * Includes same assets as eNPV: In Development (always), Idle (if selected), On Market (always)
 */
export function calculateExpectedROI(
  assets: AssetSchemaType[],
  selection: Record<string, ActionType | boolean>,
): number {
  const includedAssets = getIncludedAssets(assets, selection);

  let totalExpectedRevenues = 0;
  let totalExpectedCosts = 0;

  includedAssets.forEach((asset) => {
    // Sum all expected revenues up to horizon
    if (asset.expected_revenues) {
      totalExpectedRevenues += asset.expected_revenues.reduce(
        (sum, revenue) => sum + revenue,
        0,
      );
    }

    // Sum all expected costs up to horizon
    if (asset.expected_costs) {
      totalExpectedCosts += asset.expected_costs.reduce(
        (sum, cost) => sum + cost,
        0,
      );
    }
  });

  if (totalExpectedCosts === 0) return 0;

  return (totalExpectedRevenues - totalExpectedCosts) / totalExpectedCosts;
}

/**
 * Calculate available capital after deducting next step cost
 */
export function calculateAvailableCapital(
  startingCash: number,
  nextStepCost?: number,
): number {
  return startingCash - (nextStepCost || 0);
}

/**
 * Calculate capital change from previous cash amount
 */
export function calculateCapitalChange(
  startingCash: number,
  previousCash?: number,
): number {
  return previousCash !== undefined ? startingCash - previousCash : 0;
}

/**
 * Check if there's a capital change to display
 */
export function hasCapitalChange(
  previousCash?: number,
  capitalChange?: number,
): boolean {
  return previousCash !== undefined && (capitalChange || 0) !== 0;
}

/**
 * Check if available capital is negative (insufficient funds)
 */
export function isInsufficientCapital(
  startingCash: number,
  nextStepCost?: number,
): boolean {
  return calculateAvailableCapital(startingCash, nextStepCost) < 0;
}

/**
 * Calculate change in expected NPV from previous state
 */
export function calculateEnpvChange(
  currentExpectedNPV: number,
  previousAssets?: AssetSchemaType[],
  selection?: Record<string, ActionType | boolean>,
): number {
  if (!previousAssets || !selection) return 0;

  const previousExpectedNPV = calculateExpectedNPV(previousAssets, selection);
  return currentExpectedNPV - previousExpectedNPV;
}

/**
 * Calculate change in expected ROI from previous state
 */
export function calculateEroiChange(
  currentExpectedROI: number,
  previousAssets?: AssetSchemaType[],
  selection?: Record<string, ActionType | boolean>,
): number {
  if (!previousAssets || !selection) return 0;

  const previousExpectedROI = calculateExpectedROI(previousAssets, selection);
  return currentExpectedROI - previousExpectedROI;
}

/**
 * Check if there's an eNPV change to display
 */
export function hasEnpvChange(
  time: number,
  enpvChange: number,
  previousAssets?: AssetSchemaType[],
): boolean {
  return time !== 0 && previousAssets !== undefined && enpvChange !== 0;
}

/**
 * Check if there's an eROI change to display
 */
export function hasEroiChange(
  time: number,
  eroiChange: number,
  previousAssets?: AssetSchemaType[],
): boolean {
  return time !== 0 && previousAssets !== undefined && eroiChange !== 0;
}
