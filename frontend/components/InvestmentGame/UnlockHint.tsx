"use client";

import { useEffect, useState } from "react";
import { Button } from "../ui/button";
import { Lightbulb, Loader2 } from "lucide-react";
import { getAgents, hintGame } from "@/lib/backendCallsGame";
import { InformationButton } from "@/components/InformationButton";
import { informationDictionary } from "@/lib/information-dictionary-game";
import type {
  Agent,
  HintResponse,
  AssetSchemaType,
} from "@/lib/definitionsGameZ";
import { formatDisplayNumber } from "@/lib/numbers";

interface UnlockHintProps {
  gameId: string;
  onHintReceived: (hints: Record<string, boolean>, agentName: string) => void;
  onCashDeducted: (amount: number) => void; // Callback to deduct cash from parent
  onHintToggled: (visible: boolean, agentName?: string) => void; // Callback to toggle hint column visibility
  currentCash: number;
  resetKey?: number; // When this changes, reset the purchased agents
  assets?: Record<string, AssetSchemaType>; // Current game assets
}

export default function UnlockHint({
  gameId,
  onHintReceived,
  onCashDeducted,
  onHintToggled,
  currentCash,
  resetKey,
  assets,
}: UnlockHintProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [purchasingAgent, setPurchasingAgent] = useState<string | null>(null);
  const [purchasedAgents, setPurchasedAgents] = useState<Set<string>>(
    new Set(),
  );
  const [purchasedAgentHints, setPurchasedAgentHints] = useState<
    Record<string, Record<string, boolean>>
  >({});
  const [currentlyDisplayedAgent, setCurrentlyDisplayedAgent] =
    useState<string>("");
  const [error, setError] = useState<string>("");

  // Load agents on component mount
  useEffect(() => {
    async function fetchAgents() {
      try {
        setLoadingAgents(true);
        const agentsData = await getAgents();
        setAgents(agentsData);
      } catch (err) {
        console.error("Failed to load agents:", err);
        setError("Failed to load agents");
      } finally {
        setLoadingAgents(false);
      }
    }

    fetchAgents();
  }, []);

  // Reset purchased agents when resetKey changes
  useEffect(() => {
    setPurchasedAgents(new Set());
    setPurchasedAgentHints({});
    setCurrentlyDisplayedAgent("");
  }, [resetKey]);

  // Check if there are any assets in "Idle" state
  const hasIdleAssets =
    assets && Object.keys(assets).length > 0
      ? Object.values(assets).some((asset) => asset.state === "Idle")
      : false;

  async function handlePurchaseHint(agent: Agent) {
    if (!gameId || currentCash < agent.cost) return;

    try {
      setPurchasingAgent(agent.name);
      setError("");

      const hintResponse: HintResponse = await hintGame(gameId, agent.name);
      console.log(hintResponse);

      // Check if response contains an error message
      if (
        hintResponse &&
        typeof hintResponse === "object" &&
        "message" in hintResponse
      ) {
        setError((hintResponse as any).message);
        return;
      }

      const hints: Record<string, boolean> = {};

      // Handle new nested response format: { "AgentName": { "assetId": "invest" } }
      if (
        typeof hintResponse === "object" &&
        hintResponse !== null &&
        Object.keys(hintResponse).length > 0
      ) {
        // Check if it's the nested format with agent data
        const agentHints = (
          hintResponse as Record<string, Record<string, "invest">>
        )[agent.name];
        if (agentHints && typeof agentHints === "object") {
          Object.entries(agentHints).forEach(([assetId, action]) => {
            hints[assetId] = action === "invest";
          });
        }
      }

      onHintReceived(hints, agent.name);

      // Store hints for this agent
      setPurchasedAgentHints((prev) => ({
        ...prev,
        [agent.name]: hints,
      }));

      // Mark this agent as purchased
      setPurchasedAgents((prev) => new Set([...prev, agent.name]));

      // Set as currently displayed agent
      setCurrentlyDisplayedAgent(agent.name);

      // Deduct the cost from the displayed capital
      onCashDeducted(agent.cost);
    } catch (err) {
      console.error("Failed to purchase hint:", err);

      // Extract error message from response
      let errorMessage = `Failed to purchase hint from ${agent.name}`;
      console.log(err);

      if (err instanceof Error) {
        try {
          // Try to parse the error message as JSON
          const parsed = JSON.parse(err.message);
          if (parsed && parsed.message) {
            errorMessage = parsed.message;
          } else if (typeof parsed.detail === "string") {
            errorMessage = parsed.detail;
          }
        } catch {
          // If parsing fails, use the error message directly
          errorMessage = err.message || errorMessage;
        }
      }

      setError(errorMessage);
    } finally {
      setPurchasingAgent(null);
    }
  }

  function handleLightbulbToggle(agent: Agent) {
    const isPurchased = purchasedAgents.has(agent.name);
    if (!isPurchased) return; // Can't toggle if not purchased

    const isCurrentlyDisplayed = currentlyDisplayedAgent === agent.name;

    if (isCurrentlyDisplayed) {
      // Hide hints if this agent is currently displayed
      setCurrentlyDisplayedAgent("");
      onHintToggled(false);
    } else {
      // Show this agent's hints
      const hints = purchasedAgentHints[agent.name] || {};
      setCurrentlyDisplayedAgent(agent.name);
      onHintReceived(hints, agent.name);
      onHintToggled(true, agent.name);
    }
  }

  if (loadingAgents) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-lg bg-white p-4">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm text-gray-600">Loading agents...</span>
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="rounded-lg bg-white p-4">
        <span className="text-sm text-gray-600">No agents available</span>
      </div>
    );
  }

  return (
    <div className="w-full rounded-lg bg-white p-4 shadow-sm" id="agentsHint">
      <h3 className="mb-3 text-sm font-medium text-gray-900">
        AI Agent Hints
        {purchasedAgents.size > 0 && (
          <span className="ml-2 text-xs text-gray-500"></span>
        )}
      </h3>

      {error && (
        <div className="mb-3 rounded-md bg-red-50 p-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="space-y-2">
        {agents.map((agent) => {
          const canAfford = currentCash >= agent.cost;
          const isLoading = purchasingAgent === agent.name;
          const isPurchased = purchasedAgents.has(agent.name);
          const isDisabledDueToAssets = !hasIdleAssets;

          return (
            <div
              key={agent.name}
              className="flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">
                  {agent.name}
                </span>
                {(() => {
                  const agentKey =
                    `${agent.name.toLowerCase()}Agent` as keyof typeof informationDictionary;
                  const agentInfo = informationDictionary[agentKey];
                  return agentInfo ? (
                    <InformationButton
                      title={agentInfo.title}
                      description={agentInfo.description}
                      buttonClassName="w-4 h-4"
                    />
                  ) : null;
                })()}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  onClick={() => handlePurchaseHint(agent)}
                  disabled={
                    !canAfford ||
                    isLoading ||
                    isPurchased ||
                    isDisabledDueToAssets
                  }
                  size="sm"
                  variant={
                    canAfford && !isPurchased && !isDisabledDueToAssets
                      ? "default"
                      : "outline"
                  }
                  className="min-w-[100px]"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />£
                      {formatDisplayNumber(agent.cost)}
                    </>
                  ) : isPurchased ? (
                    <>Purchased</>
                  ) : isDisabledDueToAssets ? (
                    <>No need</>
                  ) : (
                    <>£{formatDisplayNumber(agent.cost)}</>
                  )}
                </Button>

                {/* Light Bulb Toggle Button */}
                <Button
                  onClick={() => handleLightbulbToggle(agent)}
                  disabled={!isPurchased}
                  variant="ghost"
                  size="sm"
                  className={`h-8 w-8 rounded-full p-0 ${
                    isPurchased
                      ? currentlyDisplayedAgent === agent.name
                        ? "bg-blue-500 hover:bg-blue-600"
                        : "bg-blue-100 hover:bg-blue-200"
                      : "cursor-not-allowed bg-gray-100"
                  }`}
                  title={
                    !isPurchased
                      ? "Purchase agent first to toggle hints"
                      : currentlyDisplayedAgent === agent.name
                        ? "Hide hints"
                        : "Show hints"
                  }
                >
                  <Lightbulb
                    size={16}
                    className={
                      isPurchased
                        ? currentlyDisplayedAgent === agent.name
                          ? "text-white"
                          : "text-blue-600"
                        : "text-gray-400"
                    }
                  />
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
