"use client";

import { useState, useMemo, useEffect } from "react";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { StopCircle, AlertTriangle, CheckCircle } from "lucide-react";
import { useNextStep } from "nextstepjs";
import { useCustomNextStep } from "@/hooks/use-custom-next-step";
import {
  Table,
  TableScroll,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/numbers";
import type {
  AssetSchemaType,
  TrialPhaseName,
  ActionType,
  InvestmentLevelsConfig,
} from "@/lib/definitionsGameZ";
import {
  isPhaseProgression,
  isFirstPhase,
  extractPhasesFromAssets,
  TRIAL_PHASES,
} from "@/lib/game-constants";
import AssetInfo from "./AssetInfo";
import AssetHintNo from "./AssetHintNo";
import AssetHintYes from "./AssetHintYes";

import { InformationButton } from "../InformationButton";
import { informationDictionary } from "@/lib/information-dictionary-game";

interface AssetsTableProps {
  assets: AssetSchemaType[];
  selection: Record<string, ActionType | boolean>;
  onAssetSelection: (asset: AssetSchemaType) => void;
  onInvestmentLevelChange?: (asset: AssetSchemaType, level: ActionType) => void;
  investmentLevelsEnabled?: boolean;
  investmentLevelsConfig?: InvestmentLevelsConfig | null; // Config for investment levels info popup
  interimObservationsEnabled?: boolean; // Whether interim trial observations feature is enabled
  distributionalPtrsEnabled?: boolean; // Whether distributional PTRS feature is enabled
  previousAssetStates?: Record<string, AssetSchemaType["state"]>; // Track previous states for change detection
  previousAssetPhases?: Record<string, AssetSchemaType["pending_trial_phase"]>; // Track previous phases for trial completion detection
  hints?: Record<string, boolean>; // Hints from AI agents
  hintColumnVisible?: boolean; // Whether to show the hint column
  selectedAgentName?: string; // Name of the agent that provided the current hints
  time?: number; // Current game time step
  readOnly?: boolean; // When true, all controls are disabled (for replay viewer)
  highlightedAssetIds?: Map<string, "changed" | "bd-acquisition">; // Assets to highlight (changed=amber, bd-acquisition=blue)
  actionHighlightIds?: Set<string>; // Assets where agent took an action (shown as switch halo)
}

export default function AssetsTable({
  assets,
  selection,
  onAssetSelection,
  onInvestmentLevelChange,
  investmentLevelsEnabled = false,
  investmentLevelsConfig,
  interimObservationsEnabled = false,
  distributionalPtrsEnabled = false,
  previousAssetStates = {},
  previousAssetPhases = {},
  hints = {},
  hintColumnVisible = false,
  selectedAgentName,
  time,
  readOnly = false,
  highlightedAssetIds,
  actionHighlightIds,
}: AssetsTableProps) {
  const { startNextStep } = useNextStep();
  const showIndicationColumn = assets.some((a) => !!a.indication_name);
  const { startTourIfNotSkipped } = useCustomNextStep();
  const [view, setView] = useState<"development" | "market" | "expired">(
    "development",
  );

  // Generate description for investment levels info popup
  const getInvestmentLevelsDescription = (): string => {
    if (!investmentLevelsConfig) {
      return "Investment levels allow you to control the intensity of R&D investment for each asset.";
    }

    const lines: string[] = ["Investment levels control R&D intensity:", ""];

    const levelOrder = ["minimal", "standard", "accelerated"];
    for (const levelName of levelOrder) {
      const level = investmentLevelsConfig.levels[levelName];
      if (level) {
        lines.push(
          `${levelName.charAt(0).toUpperCase() + levelName.slice(1)}:`,
        );
        lines.push(`  Cost: ${level.cost_modifier}x`);
        lines.push(`  Speed: ${level.speed_modifier}x`);
        if (level.success_modifier !== 1.0) {
          lines.push(`  Success: ${level.success_modifier}x`);
        }
        lines.push(`  Capacity: ${level.capacity_cost} units`);
        lines.push(`  Experience: ${level.experience_modifier}x`);
        lines.push("");
      }
    }

    lines.push(`R&D Capacity: ${investmentLevelsConfig.base_capacity} units`);
    lines.push(
      `Over capacity: up to ${1 - investmentLevelsConfig.overage_max_penalty}x success`,
    );
    lines.push(
      `Over capacity: up to ${1 + investmentLevelsConfig.overage_cost_max_penalty}x cost`,
    );

    return lines.join("\n");
  };

  // Extract phase order for progression logic
  const availablePhases = extractPhasesFromAssets(assets);
  const phaseOrder = TRIAL_PHASES;

  // Group assets by state
  const inDevelopmentAssets = assets.filter(
    (asset) => asset.state === "Idle" || asset.state === "In Development",
  );
  const onMarketAssets = assets.filter((asset) => asset.state === "On Market");
  const expiredAssets = assets.filter(
    (asset) => asset.state === "Expired" || asset.state === "Failed",
  );

  // Check if an asset has changed status from "In Development" to "On Market" or "Expired"/"Failed"
  // Also check for "On Market" to "Expired"/"Failed" transitions
  const hasStatusChanged = (asset: AssetSchemaType) => {
    const previousState = previousAssetStates[asset.id];
    const hasChanged =
      (previousState === "In Development" &&
        (asset.state === "On Market" ||
          asset.state === "Expired" ||
          asset.state === "Failed")) ||
      (previousState === "On Market" &&
        (asset.state === "Expired" || asset.state === "Failed"));

    return hasChanged;
  };

  // Check if an asset has completed a trial and moved to a new phase
  const hasPhaseChanged = (asset: AssetSchemaType) => {
    const previousPhase = previousAssetPhases[asset.id];
    const currentPhase = asset.pending_trial_phase;

    // If we have a previous phase and it's different from current phase,
    // and both are defined (not null), then a phase change occurred
    if (previousPhase && currentPhase && previousPhase !== currentPhase) {
      // Only count as a phase change if moving forward in the phases
      return isPhaseProgression(
        previousPhase as TrialPhaseName,
        currentPhase as TrialPhaseName,
        phaseOrder,
      );
    }

    return false;
  };

  // Check if an asset has any change (status or phase)
  const hasAnyChange = (asset: AssetSchemaType) => {
    return hasStatusChanged(asset) || hasPhaseChanged(asset);
  };

  // Check if any assets in a group have status changes
  const hasGroupChanges = useMemo(() => {
    return {
      market: onMarketAssets.some(hasAnyChange),
      expired: expiredAssets.some(hasAnyChange),
      development: inDevelopmentAssets.some(hasAnyChange),
    };
  }, [
    onMarketAssets,
    expiredAssets,
    inDevelopmentAssets,
    previousAssetStates,
    previousAssetPhases,
  ]);

  // Teal dot component for status change indicator
  const StatusChangeDot = ({
    className = "",
    asset,
  }: {
    className?: string;
    asset?: AssetSchemaType;
  }) => {
    let tooltipText = "Recent change";

    if (asset) {
      const statusChanged = hasStatusChanged(asset);
      const phaseChanged = hasPhaseChanged(asset);

      if (statusChanged && phaseChanged) {
        tooltipText = "Asset completed trial and changed status";
      } else if (statusChanged) {
        tooltipText = "Asset status recently changed";
      } else if (phaseChanged) {
        tooltipText = "Asset completed trial and moved to next phase";
      }
    }

    return (
      <div
        className={cn(
          "inline-block h-3 w-3 flex-shrink-0 rounded-full bg-teal-500",
          className,
        )}
        title={tooltipText}
      />
    );
  };

  // Helper to check if a selection value means "selected for investment"
  const isSelectionActive = (
    val: ActionType | boolean | undefined,
  ): boolean => {
    if (val === true) return true;
    if (typeof val === "string" && val !== "none" && val !== "stop")
      return true;
    return false;
  };

  // Get the current investment level for an asset
  const getCurrentInvestmentLevel = (asset: AssetSchemaType): ActionType => {
    const val = selection[asset.id];
    if (val === true) return "standard";
    if (val === false || val === undefined) return "none";
    return val;
  };

  const getToggleState = (asset: AssetSchemaType) => {
    const isIdle = asset.state === "Idle";
    const isInDevelopment = asset.state === "In Development";
    const selVal = selection[asset.id];

    // For Idle assets, use the selection state directly from parent
    if (isIdle) {
      return {
        isOn: isSelectionActive(selVal),
        isDisabled: false,
        currentLevel: getCurrentInvestmentLevel(asset),
      };
    }

    // If In Development
    if (isInDevelopment) {
      // When investment levels are enabled, allow changing level (including stop)
      if (investmentLevelsEnabled) {
        return {
          isOn: selVal !== "stop",
          isDisabled: false, // Allow changing level
          currentLevel: getCurrentInvestmentLevel(asset),
        };
      }
      // Legacy mode: always on and disabled
      return {
        isOn: true,
        isDisabled: true,
        currentLevel: "standard" as ActionType,
      };
    }

    // On Market assets should be on and disabled (they generate revenue automatically)
    if (asset.state === "On Market") {
      return {
        isOn: true,
        isDisabled: true,
        currentLevel: "none" as ActionType,
      };
    }

    // Expired or Failed assets should be off and disabled
    if (asset.state === "Expired" || asset.state === "Failed") {
      return {
        isOn: false,
        isDisabled: true,
        currentLevel: "none" as ActionType,
      };
    }

    // Default case - use parent selection
    return {
      isOn: isSelectionActive(selVal),
      isDisabled: false,
      currentLevel: getCurrentInvestmentLevel(asset),
    };
  };

  const getCurrentPhaseData = (asset: AssetSchemaType) => {
    const currentPhase = asset.pending_trial_phase;
    return asset.trials[currentPhase as keyof typeof asset.trials];
  };

  // Helper function to determine hint display logic
  const getHintDisplay = (asset: AssetSchemaType) => {
    const hasHint = hints[asset.id] !== undefined;
    const hintValue = hints[asset.id];
    const isSelected = !!selection[asset.id];
    const isIdle = asset.state === "Idle";

    // Only show hints for assets that the selected agent specifically provided recommendations for
    if (!hasHint) {
      // Special case: Show faded "No" hint for unselected idle assets with no hints
      if (!isSelected && isIdle) {
        return {
          component: <AssetHintNo />,
          className: "opacity-20",
        };
      }
      // Special case: Show full "No" hint for selected idle assets with no hints
      if (isSelected && isIdle) {
        return {
          component: <AssetHintNo />,
          className: "",
        };
      }
      return null;
    }

    // Hint available - show based on hint value
    if (hintValue) {
      // Positive hint (AI recommends this asset)
      return {
        component: <AssetHintYes />,
        className: isSelected ? "opacity-60" : "", // Slightly fade if user already selected it
      };
    } else {
      // Negative hint (AI does not recommend this asset)
      return {
        component: <AssetHintNo />,
        className: !isSelected ? "opacity-60" : "", // Slightly fade if user didn't select it
      };
    }
  };

  // Reusable table component for each tab
  const renderAssetsTable = (
    tabAssets: AssetSchemaType[],
    emptyMessage: string,
  ) => (
    <div className="rounded-md border bg-white">
      {tabAssets.length === 0 ? (
        <div className="py-8 text-center text-gray-500">{emptyMessage}</div>
      ) : (
        <TableScroll maxHeight="420px">
          <TableHeader className="sticky top-0 z-10 bg-gray-50">
            <TableRow className="bg-gray-50">
              <TableHead className="w-16">&nbsp;</TableHead>
              {hintColumnVisible && (
                <TableHead className="w-16 text-xs">
                  <div className="flex flex-col items-center">
                    <span>Hint</span>
                    {selectedAgentName && (
                      <span className="text-xs font-medium text-blue-600">
                        {selectedAgentName}
                      </span>
                    )}
                  </div>
                </TableHead>
              )}
              <TableHead>Asset Name</TableHead>
              <TableHead>
                <div className="flex items-center">
                  TA
                  <InformationButton
                    title={informationDictionary.TA.title}
                    description={informationDictionary.TA.description}
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              {showIndicationColumn && <TableHead>Indication</TableHead>}
              <TableHead>Current Phase</TableHead>
              <TableHead className="text-right">Cost This Year</TableHead>
              <TableHead>
                <div className="flex items-center text-right">
                  PTRS Estimate (%)
                  <InformationButton
                    title={informationDictionary.phasePTRS.title}
                    description={informationDictionary.phasePTRS.description}
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              {interimObservationsEnabled && (
                <TableHead>
                  <div className="flex items-center">
                    Interim Signal
                    <InformationButton
                      title={informationDictionary.interimSignal.title}
                      description={
                        informationDictionary.interimSignal.description
                      }
                      buttonClassName="w-4 h-4"
                    />
                  </div>
                </TableHead>
              )}
              <TableHead className="text-right">
                <div className="flex items-center">
                  Remaining Phase Cost
                  <InformationButton
                    title={informationDictionary.remainingPhaseCost.title}
                    description={
                      informationDictionary.remainingPhaseCost.description
                    }
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              <TableHead>Remaining Phase Time (years)</TableHead>
              <TableHead className="text-right">eNPV</TableHead>
              <TableHead>eROI</TableHead>
              <TableHead className="text-right">
                <div className="flex items-center">
                  PYS
                  <InformationButton
                    title={informationDictionary.PYS.title}
                    description={informationDictionary.PYS.description}
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              <TableHead className="text-right">
                <div className="flex items-center">
                  Time to Expiry
                  <InformationButton
                    title={informationDictionary.timeToExpiry.title}
                    description={informationDictionary.timeToExpiry.description}
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tabAssets.map((asset, idx) => {
              const toggleState = getToggleState(asset);
              const currentPhaseData = getCurrentPhaseData(asset);
              const isActionHighlighted =
                actionHighlightIds?.has(asset.id) ?? false;
              const switchRing = isActionHighlighted
                ? "ring-2 ring-teal-500 ring-offset-1 rounded-full"
                : "";

              return (
                <TableRow
                  key={asset.id}
                  id={idx === 0 ? "assetRow0" : undefined}
                  className={`transition-colors ${
                    highlightedAssetIds?.get(asset.id) === "bd-acquisition"
                      ? "bg-blue-100 shadow-[inset_4px_0_0_0_#3b82f6] hover:bg-blue-200"
                      : highlightedAssetIds?.has(asset.id)
                        ? "bg-amber-100 shadow-[inset_4px_0_0_0_#f59e0b] hover:bg-amber-200"
                        : "hover:bg-gray-50"
                  }`}
                >
                  <TableCell className="whitespace-nowrap">
                    {investmentLevelsEnabled ? (
                      // Investment level controls based on asset state
                      asset.state === "In Development" ? (
                        // In Development: Stop toggle + current level display
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={toggleState.currentLevel !== "stop"}
                            disabled={readOnly}
                            onCheckedChange={(checked) => {
                              if (onInvestmentLevelChange) {
                                onInvestmentLevelChange(
                                  asset,
                                  checked ? "standard" : "stop",
                                );
                              }
                            }}
                            className={`focus-visible:ring-teal-600 data-[state=checked]:bg-teal-600 ${switchRing}`}
                          />
                          <div className="w-[100px]">
                            {toggleState.currentLevel === "stop" ? (
                              <span
                                className="flex items-center gap-1 text-xs text-red-600"
                                title="This asset will be abandoned on the next step and cannot be restarted"
                              >
                                <StopCircle className="h-3 w-3" />
                                Abandoning
                              </span>
                            ) : (
                              <span className="text-xs capitalize text-gray-500">
                                {asset.current_investment_level || "standard"}
                              </span>
                            )}
                          </div>
                        </div>
                      ) : asset.state === "Idle" ? (
                        // Idle: Toggle + Level dropdown
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={toggleState.isOn}
                            disabled={readOnly}
                            onCheckedChange={(checked) => {
                              if (onInvestmentLevelChange) {
                                onInvestmentLevelChange(
                                  asset,
                                  checked ? "standard" : "none",
                                );
                              }
                            }}
                            className={`focus-visible:ring-teal-600 data-[state=checked]:bg-teal-600 ${switchRing}`}
                          />
                          <Select
                            value={
                              toggleState.currentLevel === "none"
                                ? "standard"
                                : toggleState.currentLevel
                            }
                            onValueChange={(value) => {
                              if (onInvestmentLevelChange) {
                                onInvestmentLevelChange(
                                  asset,
                                  value as ActionType,
                                );
                              }
                            }}
                            disabled={readOnly || !toggleState.isOn}
                          >
                            <SelectTrigger
                              className={`h-7 w-[100px] text-xs ${!toggleState.isOn ? "opacity-50" : ""}`}
                            >
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="minimal">Minimal</SelectItem>
                              <SelectItem value="standard">Standard</SelectItem>
                              <SelectItem value="accelerated">
                                Accelerated
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <InformationButton
                            title="Investment Levels"
                            description={getInvestmentLevelsDescription()}
                            buttonClassName="w-4 h-4"
                          />
                        </div>
                      ) : (
                        // Other states: disabled
                        <Switch
                          checked={toggleState.isOn}
                          disabled={true}
                          className={`focus-visible:ring-teal-600 data-[state=checked]:bg-teal-600 ${switchRing}`}
                        />
                      )
                    ) : (
                      // Simple toggle (legacy mode)
                      <Switch
                        checked={toggleState.isOn}
                        disabled={readOnly || toggleState.isDisabled}
                        onCheckedChange={() => {
                          if (!readOnly && !toggleState.isDisabled) {
                            onAssetSelection(asset);
                          }
                        }}
                        className={`focus-visible:ring-teal-600 data-[state=checked]:bg-teal-600 ${switchRing}`}
                      />
                    )}
                  </TableCell>
                  {hintColumnVisible && (
                    <TableCell className="whitespace-nowrap text-center">
                      {(() => {
                        const hintDisplay = getHintDisplay(asset);
                        return hintDisplay ? (
                          <div className="flex items-center justify-center">
                            <div className={hintDisplay.className}>
                              {hintDisplay.component}
                            </div>
                          </div>
                        ) : null;
                      })()}
                    </TableCell>
                  )}
                  <TableCell className="whitespace-nowrap font-medium">
                    <div className="flex items-center gap-2">
                      {hasAnyChange(asset) && <StatusChangeDot asset={asset} />}
                      {asset.name}
                      <div id={`assetInfo${idx}`}>
                        <AssetInfo asset={asset} />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm capitalize">
                    {asset.therapeutic_area}
                  </TableCell>
                  {showIndicationColumn && (
                    <TableCell className="text-sm capitalize">
                      {asset.indication_name || "-"}
                    </TableCell>
                  )}
                  <TableCell className="whitespace-nowrap">
                    <span className="text-sm font-medium">
                      {asset.pending_trial_phase}
                    </span>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-right font-mono">
                    {formatCurrency(
                      asset.state === "Idle"
                        ? asset.cost_to_invest_this_step
                        : asset.cost_this_step,
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-center">
                    <div className="flex items-center justify-center gap-1">
                      {currentPhaseData ? (
                        distributionalPtrsEnabled &&
                        currentPhaseData.ptrs_expected !== undefined ? (
                          <div className="flex flex-col items-center">
                            <span className="font-medium">
                              {(currentPhaseData.ptrs_expected * 100).toFixed(
                                1,
                              )}
                              %
                            </span>
                            {currentPhaseData.ptrs_range_low !== undefined &&
                              currentPhaseData.ptrs_range_high !==
                                undefined && (
                                <span className="text-xs text-gray-500">
                                  p10-p90:{" "}
                                  {(
                                    currentPhaseData.ptrs_range_low * 100
                                  ).toFixed(0)}
                                  -
                                  {(
                                    currentPhaseData.ptrs_range_high * 100
                                  ).toFixed(0)}
                                  %
                                </span>
                              )}
                            {currentPhaseData.ptrs_confidence !== undefined && (
                              <span
                                className={`text-xs ${
                                  currentPhaseData.ptrs_confidence >= 0.5
                                    ? "text-green-600"
                                    : currentPhaseData.ptrs_confidence >= 0.2
                                      ? "text-amber-600"
                                      : "text-red-600"
                                }`}
                              >
                                conf:{" "}
                                {(
                                  currentPhaseData.ptrs_confidence * 100
                                ).toFixed(0)}
                                %
                              </span>
                            )}
                          </div>
                        ) : (
                          (currentPhaseData.ptrs * 100).toFixed(1)
                        )
                      ) : (
                        "N/A"
                      )}
                    </div>
                  </TableCell>
                  {interimObservationsEnabled && (
                    <TableCell className="whitespace-nowrap text-center">
                      {asset.state === "In Development" ? (
                        currentPhaseData?.has_interim_observation ? (
                          <div className="flex items-center justify-center gap-1">
                            {currentPhaseData.interim_result === "positive" ? (
                              <>
                                <CheckCircle className="h-4 w-4 text-green-500" />
                                <span className="text-sm text-green-600">
                                  Positive
                                </span>
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                                <span className="text-sm text-amber-600">
                                  Negative
                                </span>
                              </>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400">Pending</span>
                        )
                      ) : (
                        <span className="text-gray-300">-</span>
                      )}
                    </TableCell>
                  )}
                  <TableCell className="whitespace-nowrap pr-10 text-right font-mono">
                    {formatCurrency(currentPhaseData?.cost_remaining ?? 0)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-center">
                    {currentPhaseData?.time_remaining ?? 0}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-right font-mono">
                    {formatCurrency(asset.enpv ?? 0)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-center">
                    x{asset.eroi.toFixed(1)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-right font-mono">
                    {formatCurrency(asset.max_revenue)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-center">
                    {asset.time_until_patent_expiry}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </TableScroll>
      )}
    </div>
  );

  // Specialized table component for "On Market" assets
  const renderOnMarketTable = (
    tabAssets: AssetSchemaType[],
    emptyMessage: string,
  ) => (
    <div className="rounded-md border bg-white">
      {tabAssets.length === 0 ? (
        <div className="py-8 text-center text-gray-500" id="onMarketTable">
          {emptyMessage}
        </div>
      ) : (
        <TableScroll id="onMarketTable" maxHeight="500px">
          <TableHeader className="sticky top-0 z-10 bg-gray-50">
            <TableRow className="bg-gray-50">
              <TableHead>Asset Name</TableHead>
              <TableHead>
                <div className="flex items-center">
                  TA
                  <InformationButton
                    title={informationDictionary.TA.title}
                    description={informationDictionary.TA.description}
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              {showIndicationColumn && <TableHead>Indication</TableHead>}
              <TableHead className="text-right">
                <div className="flex items-center justify-end">
                  Budget Next Year
                  <InformationButton
                    title={informationDictionary.budgetNextYear.title}
                    description={
                      informationDictionary.budgetNextYear.description
                    }
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              <TableHead className="text-right">eNPV</TableHead>
              <TableHead className="text-right">
                <div className="flex items-center justify-end">
                  PYS
                  <InformationButton
                    title={informationDictionary.PYS2.title}
                    description={informationDictionary.PYS2.description}
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              <TableHead>
                <div className="flex items-center justify-end">
                  Time from launch to PYS
                  <InformationButton
                    title={informationDictionary.timeFromLaunchToPYS.title}
                    description={
                      informationDictionary.timeFromLaunchToPYS.description
                    }
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
              <TableHead>Time on Market</TableHead>
              <TableHead>
                <div className="flex items-center justify-end">
                  Time to Expiry
                  <InformationButton
                    title={informationDictionary.timeToExpiry.title}
                    description={informationDictionary.timeToExpiry.description}
                    buttonClassName="w-4 h-4"
                  />
                </div>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tabAssets.map((asset) => (
              <TableRow
                key={asset.id}
                className="transition-colors hover:bg-gray-50"
              >
                <TableCell className="whitespace-nowrap font-medium">
                  <div className="flex items-center gap-2">
                    {hasAnyChange(asset) && <StatusChangeDot asset={asset} />}
                    {asset.name}
                    <AssetInfo asset={asset} />
                  </div>
                </TableCell>
                <TableCell className="text-sm capitalize">
                  {asset.therapeutic_area}
                </TableCell>
                <TableCell className="text-sm capitalize">
                  {asset.indication_name || "-"}
                </TableCell>
                <TableCell className="whitespace-nowrap text-right font-mono">
                  {formatCurrency(asset.revenue_this_step)}
                </TableCell>
                <TableCell className="whitespace-nowrap text-right font-mono">
                  {formatCurrency(asset.enpv ?? 0)}
                </TableCell>
                <TableCell className="whitespace-nowrap text-right font-mono">
                  {formatCurrency(asset.max_revenue)}
                </TableCell>
                <TableCell className="whitespace-nowrap text-center">
                  {asset.time_until_max_revenue}
                </TableCell>
                <TableCell className="whitespace-nowrap text-center">
                  {asset.time_on_market}
                </TableCell>
                <TableCell className="whitespace-nowrap text-center">
                  {asset.time_until_patent_expiry}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </TableScroll>
      )}
    </div>
  );

  // Specialized table component for "Expired" assets
  const renderExpiredTable = (
    tabAssets: AssetSchemaType[],
    emptyMessage: string,
  ) => (
    <div className="rounded-md border bg-white">
      {tabAssets.length === 0 ? (
        <div className="py-8 text-center text-gray-500" id="expiredTable">
          {emptyMessage}
        </div>
      ) : (
        <TableScroll id="expiredTable" maxHeight="500px">
          <TableHeader className="sticky top-0 z-10 bg-gray-50">
            <TableRow className="bg-gray-50">
              <TableHead>Asset Name</TableHead>
              <TableHead>TA</TableHead>
              {showIndicationColumn && <TableHead>Indication</TableHead>}
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tabAssets.map((asset) => (
              <TableRow
                key={asset.id}
                className="transition-colors hover:bg-gray-50"
              >
                <TableCell className="whitespace-nowrap font-medium">
                  <div className="flex items-center gap-2">
                    {hasAnyChange(asset) && <StatusChangeDot asset={asset} />}
                    {asset.name}
                    <AssetInfo asset={asset} />
                  </div>
                </TableCell>
                <TableCell className="text-sm capitalize">
                  {asset.therapeutic_area}
                </TableCell>
                <TableCell className="text-sm capitalize">
                  {asset.indication_name || "-"}
                </TableCell>
                <TableCell className="whitespace-nowrap text-sm capitalize">
                  {asset.state}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </TableScroll>
      )}
    </div>
  );

  return (
    <div className="w-full">
      {/* Custom Tab Navigation */}
      <div className="flex space-x-2 bg-gray-100 p-4 text-sm">
        <div id="assetTabNav" className="flex space-x-2">
        <div
          className={cn(
            "flex cursor-pointer items-center gap-2 rounded-lg px-4 py-2",
            {
              "bg-gray-200 font-bold": view === "development",
            },
          )}
          onClick={() => setView("development")}
          id="assetDevelopment"
        >
          {hasGroupChanges.development && (
            <StatusChangeDot className="flex-shrink-0" />
          )}
          In Development ({inDevelopmentAssets.length})
        </div>
        <div
          className={cn(
            "flex cursor-pointer items-center gap-2 rounded-lg px-4 py-2",
            {
              "bg-gray-200 font-bold": view === "market",
            },
          )}
          onClick={() => {
            setView("market");
            startTourIfNotSkipped("actionScreenOnMarket", startNextStep);
          }}
          id="assetMarket"
        >
          {hasGroupChanges.market && (
            <StatusChangeDot className="flex-shrink-0" />
          )}
          On Market ({onMarketAssets.length})
        </div>
        <div
          className={cn(
            "flex cursor-pointer items-center gap-2 rounded-lg px-4 py-2",
            {
              "bg-gray-200 font-bold": view === "expired",
            },
          )}
          onClick={() => {
            setView("expired");
            startTourIfNotSkipped("actionScreenExpiredFailed", startNextStep);
          }}
          id="assetExpired"
        >
          {hasGroupChanges.expired && (
            <StatusChangeDot className="flex-shrink-0" />
          )}
          Expired/Failed ({expiredAssets.length})
        </div>
        </div>
      </div>

      {/* Tab Content */}
      {view === "development" &&
        renderAssetsTable(inDevelopmentAssets, "No assets in development")}
      {view === "market" &&
        renderOnMarketTable(onMarketAssets, "No assets on market")}
      {view === "expired" &&
        renderExpiredTable(expiredAssets, "No expired assets")}
    </div>
  );
}
