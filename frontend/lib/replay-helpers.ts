import type {
  GameStepSchemaType,
  AgentActionRecord,
  PlaythroughMetadata,
} from "./definitionsGameZ";

export type HighlightType = "changed" | "bd-acquisition";

export const AGENT_COLORS = [
  "#1CA8C0", // teal
  "#fe7800", // orange
  "#DA97C0", // pink
  "#54278F", // purple
  "#4CAF50", // green
  "#E91E63", // magenta
];

export function getAgentColorMap(agentIds: string[]): Record<string, string> {
  return Object.fromEntries(
    agentIds.map((id, i) => [id, AGENT_COLORS[i % AGENT_COLORS.length]]),
  );
}

/**
 * Build a mapping from agent_id to display name.
 * Falls back to the raw agent_id if no name is provided.
 */
export function getAgentDisplayNames(
  metadata: PlaythroughMetadata,
): Record<string, string> {
  const names = metadata.agent_names ?? {};
  return Object.fromEntries(
    metadata.agent_ids.map((id) => [id, names[id] ?? id]),
  );
}

export function computeChangedAssetIds(
  currentStates: Record<string, GameStepSchemaType>,
  previousStates: Record<string, GameStepSchemaType> | null,
): Record<string, Map<string, HighlightType>> {
  const result: Record<string, Map<string, HighlightType>> = {};

  for (const agentId of Object.keys(currentStates)) {
    const highlights = new Map<string, HighlightType>();
    const currentAssets = {
      ...currentStates[agentId].assets,
      ...currentStates[agentId].expired_assets,
    };
    const previousAssets = previousStates
      ? {
          ...previousStates[agentId]?.assets,
          ...previousStates[agentId]?.expired_assets,
        }
      : {};

    for (const [assetId, asset] of Object.entries(currentAssets)) {
      const prevAsset = previousAssets[assetId];
      if (!prevAsset) {
        // New asset — check if it's a BD acquisition
        highlights.set(
          assetId,
          asset.type === "BD" ? "bd-acquisition" : "changed",
        );
      } else if (
        prevAsset.state !== asset.state ||
        prevAsset.pending_trial_phase !== asset.pending_trial_phase
      ) {
        // Skip Idle→In Development — that's just the agent investing,
        // already shown by the row's green teal styling
        const isInvestmentStart =
          prevAsset.state === "Idle" && asset.state === "In Development";
        if (!isInvestmentStart) {
          highlights.set(assetId, "changed");
        }
      }
    }

    result[agentId] = highlights;
  }

  return result;
}

export function computeActionHighlights(
  actions: Record<string, AgentActionRecord> | null,
): Record<string, Set<string>> {
  if (!actions) return {};
  const result: Record<string, Set<string>> = {};

  for (const [agentId, action] of Object.entries(actions)) {
    const highlighted = new Set<string>();
    for (const [assetId, decision] of Object.entries(
      action.investment_decisions,
    )) {
      if (decision !== "none") {
        highlighted.add(assetId);
      }
    }
    result[agentId] = highlighted;
  }

  return result;
}
