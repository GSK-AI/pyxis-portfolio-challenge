import type {
  AssetSchemaType,
  GameStepSchemaType,
  DataType,
  ActionType,
} from "@/lib/definitionsGameZ";
import { isSelectionActive } from "@/lib/investment-game-calculations";

/**
 * Calculates the maximum Y-axis value for charts, considering all possible asset combinations
 * to ensure a fixed y-axis when user toggles selections
 */
export function calculateChartYAxisMax({
  assets,
  horizon,
  dataType,
  currentTime,
  gameState,
  bufferPercentage = 0.2,
  minDomain = 10,
}: {
  assets: AssetSchemaType[];
  horizon: number;
  dataType: DataType;
  currentTime?: number;
  gameState?: GameStepSchemaType;
  bufferPercentage?: number;
  minDomain?: number;
}): number {
  // Filter assets based on data type to get all potentially relevant assets
  const allAssets = assets.filter((asset) => {
    if (dataType === "revenue") {
      return (
        asset.state === "On Market" ||
        asset.state === "In Development" ||
        asset.state === "Idle"
      );
    } else {
      return asset.state === "In Development" || asset.state === "Idle";
    }
  });

  let maxPossibleValue = 0;

  // Calculate max possible value across all time points if all selectable assets were included
  for (let time = 0; time <= horizon; time++) {
    let totalForThisTime = 0;

    allAssets.forEach((asset, assetIndex) => {
      const expectedDataArray =
        dataType === "cost"
          ? asset.expected_costs || []
          : asset.expected_revenues || [];

      let value = 0;
      if (time === 0) {
        value = 0;
      } else if (
        currentTime !== undefined &&
        time <= currentTime &&
        gameState
      ) {
        const realisedArray = gameState
          ? dataType === "cost"
            ? gameState.realised_costs || []
            : gameState.realised_revenues || []
          : [];

        // For realised data, only assign the total to the first asset (index 0)
        // to avoid counting the same realised total multiple times
        if (assetIndex === 0) {
          const totalRealised =
            time <= realisedArray.length ? realisedArray[time - 1] : 0;
          value = totalRealised;
        } else {
          value = 0;
        }
      } else {
        const expectedIndex = time - (currentTime || 0) - 1;
        value =
          expectedIndex >= 0 && expectedIndex < expectedDataArray.length
            ? expectedDataArray[expectedIndex]
            : 0;
      }

      // Only add if asset is always included or could be selected
      if (
        asset.state === "In Development" ||
        asset.state === "On Market" ||
        asset.state === "Idle"
      ) {
        totalForThisTime += value / 1000000; // Convert to millions
      }
    });

    maxPossibleValue = Math.max(maxPossibleValue, totalForThisTime);
  }

  const calculatedMax = Math.ceil(maxPossibleValue);
  const buffer = Math.max(2, Math.ceil(calculatedMax * bufferPercentage));
  const finalMax = Math.max(minDomain, calculatedMax + buffer);

  return finalMax;
}

/**
 * Processes asset data for chart visualization
 */
export function processAssetDataForChart({
  assets,
  selection,
  horizon,
  dataType,
  currentTime,
  gameState,
  hintCosts = 0,
}: {
  assets: AssetSchemaType[];
  selection: Record<string, ActionType | boolean>;
  horizon: number;
  dataType: DataType;
  currentTime?: number;
  gameState?: GameStepSchemaType;
  hintCosts?: number;
}) {
  const relevantAssets = assets.filter((asset) => {
    const selVal = selection[asset.id];

    if (dataType === "revenue") {
      return (
        asset.state === "On Market" ||
        (asset.state === "In Development" && selVal !== "stop") ||
        (asset.state === "Idle" && isSelectionActive(selVal))
      );
    } else {
      return (
        (asset.state === "In Development" && selVal !== "stop") ||
        (asset.state === "Idle" && isSelectionActive(selVal))
      );
    }
  });

  const alwaysIncluded = relevantAssets.filter(
    (asset) => asset.state === "In Development" || asset.state === "On Market",
  );
  const selectedAssets = relevantAssets.filter(
    (asset) => asset.state === "Idle" && selection[asset.id],
  );

  const orderedAssets = [...alwaysIncluded, ...selectedAssets];

  // Get realised data once (global totals)
  const realisedArray = gameState
    ? dataType === "cost"
      ? gameState.realised_costs || []
      : gameState.realised_revenues || []
    : [];

  // If no assets to process but we have realized data or hint costs, create a simple data series for historical data
  if (
    orderedAssets.length === 0 &&
    currentTime !== undefined &&
    ((realisedArray.length > 0 && currentTime > 0) ||
      (hintCosts > 0 && dataType === "cost"))
  ) {
    const realisedSeries = [];

    for (let time = 0; time <= horizon; time++) {
      let value = 0;

      if (time > 0 && time <= currentTime) {
        if (time <= realisedArray.length) {
          value = realisedArray[time - 1]; // Get realized value for this time step
        }
      }

      // Add hint costs to the current time step for cost data (even if no other realized costs)
      if (time === currentTime && dataType === "cost" && hintCosts > 0) {
        value += hintCosts;
      }
      realisedSeries.push({
        time,
        value,
        assetId: "historical-data",
        assetName: "Historical Data",
        isSelected: true,
      });
    }

    return [realisedSeries];
  }

  const assetDataSeries = orderedAssets.map((asset, assetIndex) => {
    const expectedDataArray =
      dataType === "cost"
        ? asset.expected_costs || []
        : asset.expected_revenues || [];
    const isSelected = asset.state === "Idle" && selection[asset.id];

    const assetSeries = [];

    for (let time = 0; time <= horizon; time++) {
      let value = 0;

      if (time >= 0 && time < realisedArray.length && gameState) {
        // For realised data, only show the total on the first asset to avoid duplication
        let totalRealised = realisedArray[time]; // Get realized value for this time step

        // Add hint costs to the current time step for cost data (even if no other realized costs)
        if (time === currentTime && dataType === "cost" && hintCosts > 0) {
          totalRealised += hintCosts;
        }

        value = assetIndex === 0 ? totalRealised : 0;
      } else if (time >= realisedArray.length) {
        // Expected data starts after realized data
        const expectedIndex = time - realisedArray.length;
        value =
          expectedIndex >= 0 && expectedIndex < expectedDataArray.length
            ? expectedDataArray[expectedIndex]
            : 0;
      }

      assetSeries.push({
        time,
        value,
        assetId: asset.id,
        assetName: asset.name,
        isSelected,
      });
    }

    assetSeries.sort((a, b) => a.time - b.time);
    return assetSeries;
  });

  return assetDataSeries;
}
