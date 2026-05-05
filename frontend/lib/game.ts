import {
  AssetSchemaType,
  GameStepSchemaType,
  TrialPhaseType,
} from "./definitionsGameZ";

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

  const { assets, expired_assets } = state;

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

  return returnAssets;
}

export function assetActiveTrial(
  asset: AssetSchemaType,
): TrialPhaseType | undefined {
  const { pending_trial_phase } = asset;
  return asset.trials[pending_trial_phase as keyof typeof asset.trials];
}

export function extractAssetTrials(asset: AssetSchemaType): TrialPhaseType[] {
  if (!asset) return [];

  const { trials } = asset;

  const returnAssets: TrialPhaseType[] = [];
  Object.keys(trials).forEach((_: string) => {
    const trial = trials[_ as keyof typeof trials];
    if (trial) {
      returnAssets.push({
        cost_remaining: trial.cost_remaining ?? 0,
        time_remaining: trial.time_remaining ?? 0,
        ptrs: trial.ptrs ?? 0,
      });
    }
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
