import { AssetSchemaType, GameStepSchemaType } from "./definitionsGameZ";

export function extractAssets(state: GameStepSchemaType): AssetSchemaType[] {
  if (!state) return [];

  const { assets } = state;

  const returnAssets: AssetSchemaType[] = [];
  Object.keys(assets).forEach((_: string) => {
    returnAssets.push({
      ...assets[_],
    });
  });

  return returnAssets;
}

export function extractAllAssets(state: GameStepSchemaType): AssetSchemaType[] {
  if (!state) return [];

  const { assets, expired_assets, dropped_assets } = state;

  const returnAssets: AssetSchemaType[] = [];

  // Add regular assets
  Object.keys(assets).forEach((_: string) => {
    returnAssets.push({
      ...assets[_],
    });
  });

  // Add expired assets
  Object.keys(expired_assets).forEach((_: string) => {
    returnAssets.push({
      ...expired_assets[_],
    });
  });

  // Add voluntarily dropped assets (drop_action feature)
  Object.keys(dropped_assets ?? {}).forEach((_: string) => {
    returnAssets.push({
      ...dropped_assets[_],
    });
  });

  return returnAssets;
}

export function calculateTrialCost(asset: AssetSchemaType): number {
  // Use cost_to_invest_this_step for Idle assets, cost_this_step for InDevelopment
  if (asset.state === "Idle") {
    return asset.cost_to_invest_this_step || 0;
  }
  return asset.cost_this_step || 0;
}
