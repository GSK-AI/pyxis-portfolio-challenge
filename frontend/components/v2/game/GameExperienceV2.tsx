"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useNextStep } from "nextstepjs";
import { TriangleAlert } from "lucide-react";
import { useCustomNextStep } from "@/hooks/use-custom-next-step";
import type {
  GameStepResponse,
  MultiAgentGameStep,
} from "@/lib/definitionsGameZ";
import { GameTopBar } from "./ui/GameTopBar";
import { StatGroup, type StatProps } from "./ui/Stat";
import {
  CompetitorCard,
  RankBadge,
  type CompetitorInfo,
} from "./ui/Competitors";
import { GameOverDialog, type Standing } from "./ui/GameOverDialog";
import { CapitalChart } from "./ui/CapitalChart";
import { ProjectionChart, type ProjectionSeries } from "./ui/ProjectionChart";
import {
  processAssetDataForChart,
  calculateChartYAxisMax,
} from "@/lib/game-data";
import {
  TRIAL_PHASES,
  isPhaseProgression,
  isFirstPhase,
} from "@/lib/game-constants";
import {
  isSelectionActive,
  calculateExpectedNPV,
  calculateExpectedROI,
  calculateAvailableCapital,
  isInsufficientCapital,
} from "@/lib/investment-game-calculations";
import { calculateTrialCost } from "@/lib/game";
import type { ActionType, TrialPhaseName } from "@/lib/definitionsGameZ";
import TAExperience from "@/components/InvestmentGame/TAExperience";
import RDCapacity from "@/components/InvestmentGame/RDCapacity";
import UnlockHint from "@/components/InvestmentGame/UnlockHint";
import {
  AssetTable,
  AssetTabsBar,
  AssetLegend,
  type AssetRow,
  type AssetTab,
  type AssetTabKey,
  type HighlightFilter,
} from "./ui/AssetTable";
import type { AssetSchemaType } from "@/lib/definitionsGameZ";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatDisplayNumber } from "@/lib/numbers";
import { cn } from "@/lib/utils";
import { informationDictionary } from "@/lib/information-dictionary-game";
import { InfoHint } from "./ui/InfoHint";
import { BoardsPanel, type BoardSection } from "./ui/BoardsPanel";
import { RailButton } from "./ui/PanelRail";
import {
  FlaskConical,
  LineChart,
  Radar,
  Bell,
  Building2,
  Megaphone,
  Sparkles,
  PanelRightOpen,
  PanelRightClose,
  GraduationCap,
  Gauge,
  Lightbulb,
} from "lucide-react";
import { EmptyState } from "./ui/EmptyState";
import { ClinicalSitesBoard } from "./ui/ClinicalSitesBoard";
import { BDMarketBoard } from "./ui/BDMarketBoard";
import { SalesMarketBoard } from "./ui/SalesMarketBoard";
import { IntelligenceBoard } from "./ui/IntelligenceBoard";
import { DemandCreationBoard } from "./ui/DemandCreationBoard";
import { BrandEquityBoard } from "./ui/BrandEquityBoard";
import { LeaderboardPanel } from "./ui/LeaderboardPanel";
import { Trophy } from "lucide-react";
import { BD_MARKET_INFO } from "@/components/InvestmentGame/BDMarketPanel";
import { CLINICAL_SITES_INFO } from "@/components/InvestmentGame/ClinicalSitesPanel";
import { SALES_MARKET_INFO } from "@/components/InvestmentGame/SalesMarketPanel";
import { ALERTS_INFO } from "@/components/InvestmentGame/AlertsPanel";
import { DEMAND_CREATION_INFO } from "@/components/InvestmentGame/DemandCreationPanel";
import { BRAND_EQUITY_INFO } from "@/components/InvestmentGame/BrandEquityPanel";
import { Handshake } from "lucide-react";

/**
 * New game experience — developed iteratively behind the "New Experience"
 * toggle on the start screen. Pure UI: receives the same live game state
 * as the classic ActionGame / MultiAgentAction views and never owns logic.
 */

/** One-shot actions collected in the UI and submitted with Next Year. */
export interface TurnIntents {
  /**
   * Classic-shaped selection: `true` = invest (legacy mode); strings are
   * investment levels ("minimal" | "standard" | "accelerated") or "stop"
   * when investment levels are enabled.
   */
  invest: Record<string, ActionType | boolean>;
  readings: Record<string, number>;
  drop: Record<string, boolean>;
  buySite: boolean;
  siteBid: number;
  bdBids: number[];
  /** Sticky marketing toggles (persist across turns like the classic UI). */
  demandCreation: Record<string, number>;
  brandEquity: Record<string, number>;
}

interface GameExperienceV2Props {
  mode: "single" | "multi";
  state?: GameStepResponse | MultiAgentGameStep;
  onExit: () => void;
  onRestart: () => void;
  /** Replay the exact same game (same seed) — classic single-player. */
  onRestartSameGame?: () => void;
  /** Advances one year on the backend and updates the state upstream. */
  onNextYear: (intents: TurnIntents) => Promise<void>;
  /** Cap for the PvP clinical-site auction bid (GBP). */
  siteMaxBid?: number;
  /** Cap for BD auction bids (GBP). */
  bdMaxBid?: number;
}

/** Previous-turn snapshot for change detection (classic AssetsTable logic). */
interface TurnSnapshot {
  gameId: string;
  time: number;
  states: Record<string, AssetSchemaType["state"]>;
  phases: Record<string, AssetSchemaType["pending_trial_phase"]>;
  ids: Set<string>;
}

// Map a live asset onto a table row; the invest/readings overlays come
// from this turn's collected intents. Also reused by the v2 replay viewer.
// `invest` takes the classic-shaped selection value: booleans in legacy
// mode, level strings / "stop" when investment levels are enabled.
export function toAssetRow(
  asset: AssetSchemaType,
  selectionValue: ActionType | boolean,
  readings: number,
  dropped = false,
  changed = false,
  highlight?: "changed" | "bd",
  locked = false,
): AssetRow {
  const phase = asset.pending_trial_phase
    ? asset.trials[asset.pending_trial_phase]
    : undefined;
  const invest =
    selectionValue === true ||
    (typeof selectionValue === "string" &&
      selectionValue !== "none" &&
      selectionValue !== "stop" &&
      selectionValue !== "drop");
  return {
    id: asset.id,
    name: asset.name,
    ta: asset.therapeutic_area,
    indication: asset.indication_name,
    phase: asset.pending_trial_phase ?? asset.state,
    // Classic: Idle assets show what investing would cost
    // (cost_to_invest_this_step), others their committed cost.
    costThisYear: calculateTrialCost(asset),
    ptrs: (phase?.ptrs_expected ?? phase?.ptrs ?? 0) * 100,
    ptrsEff: phase?.ptrs_effective_readings ?? 0,
    readings,
    readingsFree: readings === 0,
    readingCosts: asset.ptrs_reading_costs,
    remainingPhaseCost: phase?.cost_remaining ?? 0,
    remainingPhaseTime: phase?.time_remaining ?? 0,
    cashEnpv: asset.cash_enpv,
    businessEnpv: asset.enpv,
    eroi: asset.eroi,
    pys: asset.max_revenue,
    timeToExpiry: asset.time_until_patent_expiry,
    // Distributional PTRS extras (classic AssetsTable display).
    ptrsRangeLow: phase?.ptrs_range_low,
    ptrsRangeHigh: phase?.ptrs_range_high,
    ptrsConfidence: phase?.ptrs_confidence,
    // Interim trial signal (classic Interim Signal column).
    interim:
      asset.state === "In Development"
        ? phase?.has_interim_observation
          ? phase.interim_result === "positive"
            ? "positive"
            : "negative"
          : "pending"
        : "na",
    // On Market extras (classic market table columns).
    revenueThisStep: asset.revenue_this_step,
    timeToPys: asset.time_until_max_revenue,
    timeOnMarket: asset.time_on_market,
    invest,
    level:
      typeof selectionValue === "string"
        ? selectionValue
        : selectionValue
          ? "standard"
          : "none",
    stopping: selectionValue === "stop",
    currentLevel: asset.current_investment_level ?? null,
    dropAvailable: asset.available_actions?.includes("drop") ?? false,
    // Drop fee: 25% of the remaining trial cost in the current phase
    // (backend drop_action rule); free once on market.
    dropFee:
      asset.state === "On Market" ? 0 : 0.25 * (phase?.cost_remaining ?? 0),
    inDevelopment: asset.state === "In Development",
    locked,
    dropped,
    changed,
    highlight,
    infoAsset: asset,
  };
}

export default function GameExperienceV2({
  mode,
  state,
  onExit,
  onRestart,
  onRestartSameGame,
  onNextYear,
  siteMaxBid = 100_000 * 1e6,
  bdMaxBid = 100_000 * 1e6,
}: GameExperienceV2Props) {
  const [advancing, setAdvancing] = useState(false);
  const [error, setError] = useState("");
  const [showAllCompetitors, setShowAllCompetitors] = useState(false);
  const [assetTab, setAssetTab] = useState<AssetTabKey>("development");
  const [showResults, setShowResults] = useState(false);
  const [boardsOpen, setBoardsOpen] = useState(false);
  const [leaderboardOpen, setLeaderboardOpen] = useState(false);
  const [activeBoard, setActiveBoard] = useState(
    mode === "multi" ? "sites" : "hints",
  );
  const [invests, setInvests] = useState<Record<string, ActionType | boolean>>(
    {},
  );
  // The selection submitted with the last accepted turn — drives the
  // classic carry-forward rule when seeding the next turn's defaults.
  const prevSelectionRef = useRef<Record<string, ActionType | boolean>>({});
  const [readings, setReadings] = useState<Record<string, number>>({});
  const [drops, setDrops] = useState<Record<string, boolean>>({});
  const [buySite, setBuySite] = useState(false);
  const [siteBid, setSiteBid] = useState(0);
  const [bdBids, setBdBids] = useState<number[]>([]);
  // Marketing toggles are sticky across turns (classic behavior): spend
  // sustains until the player switches it off.
  const [demandCreation, setDemandCreation] = useState<Record<string, number>>(
    {},
  );
  const [brandEquity, setBrandEquity] = useState<Record<string, number>>({});
  const [prevSnapshot, setPrevSnapshot] = useState<TurnSnapshot | null>(null);
  const lastSeenRef = useRef<TurnSnapshot | null>(null);
  // Opponent "thinking" simulation (classic): agents mull briefly at the
  // start of each turn; Next Year waits until everyone has decided.
  const [agentThinking, setAgentThinking] = useState<
    Record<string, "thinking" | "decided">
  >({});
  // Focus view: an alternate arrangement that collapses the dashboard
  // into one row (rank/NCF move to the top bar, standings drop out) so
  // the asset table gets the vertical space. Toggled from the top bar;
  // never sticky — every game lands on the full dashboard.
  const [focusView, setFocusView] = useState(false);
  const handleFocusViewChange = (next: boolean) => {
    setFocusView(next);
    // The charts board only exists in focus view — leaving it open would
    // strand the accordion on a section that is no longer rendered.
    if (!next) {
      setActiveBoard((prev) =>
        prev === "charts" ? (mode === "multi" ? "sites" : "hints") : prev,
      );
    }
  };
  // Focus view: legend + filter live beside the tabs (outside the table).
  const [tableFilter, setTableFilter] = useState<HighlightFilter>(null);

  // Single-player AI hints (classic UnlockHint): purchased recommendations
  // shown as a table column; spend reduces displayed capital this turn.
  const [hints, setHints] = useState<Record<string, boolean>>({});
  const [hintCosts, setHintCosts] = useState(0);
  const [hintColumnVisible, setHintColumnVisible] = useState(false);
  const [selectedAgentName, setSelectedAgentName] = useState("");

  // --- onboarding tour ---
  // Two scripts (see lib/tours/gameOnboarding): the winning condition and
  // the side panels differ enough between the modes to be worth it.
  const tourName = mode === "multi" ? "gameV2Multi" : "gameV2Single";
  const { startNextStep, closeNextStep } = useNextStep();
  const { startTourIfNotSkipped, markTourCompleted } = useCustomNextStep();
  const startTour = useCallback(() => {
    // The ? button is an explicit ask, so it replays regardless of the
    // cookie — and marking it done here means abandoning the replay
    // half-way doesn't re-arm the automatic first-run tour.
    markTourCompleted(tourName);
    startNextStep(tourName);
  }, [markTourCompleted, startNextStep, tourName]);

  // Both step shapes expose time (0-based) and horizon.
  const year = (state?.time ?? 0) + 1;
  const totalYears = state?.horizon ?? 100;
  // The backend can also signal the end via a step error (classic parity).
  const [forcedEnd, setForcedEnd] = useState(false);
  const gameEnded = (state?.game_ended ?? false) || forcedEnd;

  // The player's own step state (multi wraps it in player_state).
  const playerState =
    state && "player_state" in state ? state.player_state : state;
  const allAssets = Object.values(playerState?.assets ?? {});
  const levelsEnabled = playerState?.investment_levels_enabled ?? false;

  const cash = playerState?.cash;
  const enpv = playerState?.enpv_over_time.at(-1);
  const eroi = playerState?.eroi_over_time.at(-1);

  // Scoreboard (multi only): net cash flow = cumulative reward. Ranks are
  // classic OpponentBar semantics: sort everyone by cumulative reward and
  // assign distinct sequential positions (ties broken by sort order).
  const multiState = state && "player_state" in state ? state : undefined;
  const netCashFlow = multiState?.player_cumulative_reward;
  const rankMap = new Map<string, number>();
  if (multiState) {
    const entries = [
      { key: "__player__", reward: multiState.player_cumulative_reward },
      ...multiState.opponents.map((o) => ({
        key: o.agent_name,
        reward: o.cumulative_reward,
      })),
    ].sort((a, b) => b.reward - a.reward);
    entries.forEach((entry, i) => rankMap.set(entry.key, i + 1));
  }
  const rank = multiState ? rankMap.get("__player__") : undefined;

  const competitors: CompetitorInfo[] = multiState
    ? multiState.opponents
        .map((opponent) => ({
          name: opponent.display_name,
          agentType: opponent.agent_type,
          rank: rankMap.get(opponent.agent_name) ?? multiState.opponents.length,
          ready: agentThinking[opponent.agent_name] !== "thinking",
          bankrupt:
            opponent.game_ended &&
            !(opponent.ended_reason ?? "").includes("horizon"),
          netCashFlow: opponent.cumulative_reward,
          cash: opponent.cash,
          onMarket: opponent.num_on_market,
          inDev: opponent.num_in_development,
          enpv: opponent.enpv,
        }))
        .sort((a, b) => a.rank - b.rank)
    : [];
  const agentsReady =
    Object.keys(agentThinking).length === 0 ||
    Object.values(agentThinking).every((s) => s === "decided");

  // Standings: you and the competitors as comparable cards, ranked by
  // net cash flow — the "why" of the rank is visible in the numbers.
  const standingCards: CompetitorInfo[] = multiState
    ? [
        {
          name: multiState.player_agent_name || "You",
          agentType: "",
          rank: rank ?? 1,
          netCashFlow: multiState.player_cumulative_reward,
          cash: cash ?? 0,
          onMarket: Object.values(playerState?.assets ?? {}).filter(
            (a) => a.state === "On Market",
          ).length,
          inDev: Object.values(playerState?.assets ?? {}).filter(
            (a) => a.state === "Idle" || a.state === "In Development",
          ).length,
          enpv: enpv ?? 0,
          isPlayer: true,
        },
        ...competitors,
      ].sort((a, b) => a.rank - b.rank)
    : [];

  // Classic-shaped selection for calculations: pending drops enter the
  // record as "drop", exactly like the classic `selection`.
  const combinedSelection: Record<string, ActionType | boolean> = {
    ...invests,
  };
  Object.entries(drops).forEach(([id, isDrop]) => {
    if (isDrop) combinedSelection[id] = "drop";
  });

  // Marketing cash spent this year (classic marketingSpendThisYear):
  // flat DC cost per sized indication + per-drug BE cost.
  const marketingSpendThisYear = playerState?.marketing_enabled
    ? Object.values(demandCreation).filter((v) => v === 1).length *
        (multiState?.dc_cost ?? 0) +
      allAssets.reduce(
        (sum, asset) =>
          sum + (brandEquity[asset.id] === 1 ? (asset.be_cost ?? 0) : 0),
        0,
      )
    : 0;

  // PTRS readings cash spent this year (classic ptrsResearchSpendThisYear):
  // each selected count maps to a cumulative cost on the asset's curve.
  const readingsSpendThisYear = playerState?.ptrs_readings_enabled
    ? Object.entries(readings).reduce((sum, [assetId, count]) => {
        if (count <= 0) return sum;
        const curve =
          allAssets.find((a) => a.id === assetId)?.ptrs_reading_costs ??
          multiState?.bd_assets.find((a) => a.asset_id === assetId)
            ?.ptrs_reading_costs ??
          [];
        return sum + (curve[count - 1] ?? 0);
      }, 0)
    : 0;

  // BD auction exposure: bids entered this turn (multi). Not guaranteed
  // spend — you only pay if you win — but it's committed exposure, so it
  // feeds the capital figure and cost chart live as you type.
  const bdBidsTotal = bdBids.reduce((sum, bid) => sum + (bid || 0), 0);

  // Drop fees: 25% of the remaining phase cost per asset marked for drop
  // (backend drop_action rule; free once on market).
  const dropFeesTotal = allAssets.reduce((sum, asset) => {
    if (!drops[asset.id] || asset.state === "On Market") return sum;
    const phase = asset.pending_trial_phase
      ? asset.trials[asset.pending_trial_phase]
      : undefined;
    return sum + 0.25 * (phase?.cost_remaining ?? 0);
  }, 0);

  // --- classic nextStepCost (MultiAgentAction), extended with BD bids
  // and drop fees so the committed figure reacts to every action ---
  // Selected idle trials + committed in-development trials (unless
  // stopped/dropped) + site purchase + marketing + readings.
  const nextStepCost = (() => {
    if (!playerState) return 0;
    let totalSpend = 0;
    let developmentSpend = 0;
    allAssets.forEach((asset) => {
      const val = combinedSelection[asset.id];
      const selectedForInvestment =
        val === true ||
        (typeof val === "string" &&
          val !== "none" &&
          val !== "stop" &&
          val !== "drop");
      if (selectedForInvestment) totalSpend += calculateTrialCost(asset);
      if (
        asset.state === "In Development" &&
        val !== "stop" &&
        val !== "drop"
      ) {
        developmentSpend += calculateTrialCost(asset);
      }
    });
    const siteSpend =
      buySite && playerState.clinical_sites_enabled
        ? playerState.next_site_purchase_cost
        : 0;
    return (
      totalSpend +
      developmentSpend +
      siteSpend +
      marketingSpendThisYear +
      readingsSpendThisYear +
      bdBidsTotal +
      dropFeesTotal
    );
  })();
  // --- end identical logic ---

  // Selection-reactive stats, classic ActionStats formulas: capital after
  // this turn's committed spend (red when overdrawn), eNPV/eROI over the
  // included assets (On Market + continuing In Development + selected Idle).
  // Classic single-player also deducts hint purchases from displayed cash.
  const effectiveCash = cash !== undefined ? cash - hintCosts : undefined;
  const availableCapital =
    effectiveCash !== undefined
      ? calculateAvailableCapital(effectiveCash, nextStepCost)
      : undefined;
  const insufficientCapital =
    effectiveCash !== undefined &&
    isInsufficientCapital(effectiveCash, nextStepCost);
  const expectedNPV = calculateExpectedNPV(allAssets, combinedSelection);
  const expectedROI = calculateExpectedROI(allAssets, combinedSelection);

  const stats: StatProps[] = [
    {
      label: "Available Capital",
      value:
        availableCapital !== undefined
          ? `£${formatDisplayNumber(availableCapital)}`
          : "—",
      size: "lg",
      tone: insufficientCapital ? "danger" : undefined,
      // Sub-line tracks the live committed spend for this turn — it moves
      // with every toggle, same driver as the main value.
      delta:
        nextStepCost > 0
          ? {
              value: `£${formatDisplayNumber(nextStepCost)} committed this year`,
              direction: "down",
            }
          : undefined,
    },
    {
      label: "eNPV",
      value: `£${formatDisplayNumber(expectedNPV)}`,
      tone: expectedNPV < 0 ? "danger" : undefined,
      // Classic multi overrides the eNPV explainer: the winner is decided
      // by net cash flow, not eNPV (verbatim classic text).
      info:
        mode === "multi"
          ? {
              title: informationDictionary.eNPV.title,
              description:
                "eNPV stands for Expected Net Present Value and is a measure of the value of your portfolio today, taking into account all its expected future costs and revenue. In multiplayer mode the winner is determined by NCF (cumulative cash flow), not eNPV.",
            }
          : informationDictionary.eNPV,
    },
    {
      label: "eROI",
      value: `x${expectedROI.toFixed(1)}`,
      tone: expectedROI < 0 ? "danger" : undefined,
      info: informationDictionary.eROI,
    },
  ];

  const handleNextYear = async () => {
    if (advancing || gameEnded) return;
    setAdvancing(true);
    setError("");
    try {
      // Classic parity: in levels mode any level/stop choice is submitted;
      // in legacy mode only Idle assets take an explicit invest action —
      // In Development continues automatically and rejects "invest".
      const invest = Object.fromEntries(
        Object.entries(invests).filter(([id, val]) => {
          const active =
            val === true || (typeof val === "string" && val !== "none");
          if (!active) return false;
          if (levelsEnabled) return true;
          return playerState?.assets?.[id]?.state === "Idle";
        }),
      );
      await onNextYear({
        invest,
        readings,
        drop: drops,
        buySite,
        siteBid,
        bdBids,
        demandCreation,
        brandEquity,
      });
      // Classic: remember the submitted selection — it seeds next turn's
      // carry-forward defaults.
      prevSelectionRef.current = invests;
      // One-shot actions: clear once the turn is accepted.
      setInvests({});
      setReadings({});
      setDrops({});
      setBuySite(false);
      setSiteBid(0);
      setBdBids([]);
      // Classic single-player: hints expire with the turn.
      setHints({});
      setHintCosts(0);
      setSelectedAgentName("");
      setHintColumnVisible(false);
    } catch (err) {
      // Classic error handling: surface the backend's detail message; a
      // "game ended / horizon" rejection means game over, not an error.
      console.error("Failed to advance year:", err);
      let message = "An unexpected error occurred";
      if (err instanceof Error) {
        try {
          const parsed = JSON.parse(err.message);
          message =
            parsed && typeof parsed.detail === "string"
              ? parsed.detail
              : err.message;
        } catch {
          message = err.message;
        }
      }
      const lower = message.toLowerCase();
      if (
        lower.includes("horizon") ||
        lower.includes("game ended") ||
        lower.includes("game over") ||
        lower.includes("already ended")
      ) {
        setForcedEnd(true);
      } else {
        setError(message);
      }
    } finally {
      setAdvancing(false);
    }
  };

  // --- classic thinking simulation (MultiAgentAction) ---
  // Each opponent "thinks" for a delay scaled to its agent type, then
  // flips to decided; runs whenever a new step loads.
  useEffect(() => {
    const opponents = multiState?.opponents;
    if (!opponents || opponents.length === 0) return;
    let cancelled = false;
    const THINKING_TIMES: Record<string, number> = {
      do_nothing: 150,
      random: 250,
      knapsack_agent: 500,
      mck_agent: 600,
    };
    const initial: Record<string, "thinking" | "decided"> = {};
    opponents.forEach((opp) => {
      initial[opp.agent_name] = "thinking";
    });
    setAgentThinking(initial);
    const timers = opponents.map((opp) => {
      const base = THINKING_TIMES[opp.agent_type] ?? 800;
      const delay = Math.min(base * (0.7 + Math.random() * 0.6), 1000);
      return setTimeout(() => {
        if (cancelled) return;
        setAgentThinking((prev) => ({
          ...prev,
          [opp.agent_name]: "decided",
        }));
      }, delay);
    });
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [multiState?.time]);
  // --- end thinking simulation ---

  // Classic parity: when the player is bankrupt but the game continues,
  // auto-advance so the market plays out to the end without input.
  const playerBankrupt = multiState?.player_bankrupt ?? false;
  useEffect(() => {
    if (!playerBankrupt || gameEnded || advancing) return;
    const timer = setTimeout(() => {
      void handleNextYear();
    }, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerBankrupt, gameEnded, advancing, year]);

  // Track the previous turn's asset states/phases/ids — the classic
  // AssetsTable change-detection inputs.
  useEffect(() => {
    if (!playerState) return;
    const everyAsset = [
      ...Object.values(playerState.assets),
      ...Object.values(playerState.expired_assets ?? {}),
      ...Object.values(playerState.dropped_assets ?? {}),
    ];
    const snapshot: TurnSnapshot = {
      gameId: playerState.id,
      time: playerState.time,
      states: Object.fromEntries(everyAsset.map((a) => [a.id, a.state])),
      phases: Object.fromEntries(
        everyAsset.map((a) => [a.id, a.pending_trial_phase]),
      ),
      ids: new Set(Object.values(playerState.assets).map((a) => a.id)),
    };
    const last = lastSeenRef.current;
    let restarted = false;
    if (
      last &&
      (last.time !== snapshot.time || last.gameId !== snapshot.gameId)
    ) {
      // Forward: previous turn becomes the baseline. Backward, or a new
      // game id (restart — even at the same year 0): clear so a fresh
      // game starts without stale change markers or leftover intents.
      restarted = last.gameId !== snapshot.gameId || last.time >= snapshot.time;
      setPrevSnapshot(restarted ? null : last);
      if (restarted) {
        setForcedEnd(false);
        setInvests({});
        setReadings({});
        setDrops({});
        setBuySite(false);
        setSiteBid(0);
        setBdBids([]);
        setDemandCreation({});
        setBrandEquity({});
        setHints({});
        setHintCosts(0);
        setSelectedAgentName("");
        setHintColumnVisible(false);
        prevSelectionRef.current = {};
      } else {
        // Classic: prune sticky brand-equity spend for assets no longer
        // live, so dead no-op spend isn't resubmitted every step.
        setBrandEquity((prev) => {
          const next: Record<string, number> = {};
          for (const [id, v] of Object.entries(prev)) {
            if (playerState.assets[id]) next[id] = v;
          }
          return Object.keys(next).length === Object.keys(prev).length
            ? prev
            : next;
        });
      }
    }

    // --- classic Idle auto-selection defaults (MultiAgentAction) ---
    // Fill only assets with no explicit choice yet: off at time 0 and for
    // first-phase trials; on at start of game or after a forward phase
    // progression; otherwise carry the previous turn's selection forward.
    const prevPhases = last && last.time < snapshot.time ? last.phases : {};
    const isStartOfGame = last === null;
    const seedLevels = playerState.investment_levels_enabled ?? false;
    setInvests((current) => {
      const next = { ...current };
      let changedAny = false;
      for (const asset of Object.values(playerState.assets)) {
        if (asset.state !== "Idle" || next[asset.id] !== undefined) continue;
        const pendingPhase = asset.pending_trial_phase;
        const previousPhase = prevPhases[asset.id];
        const prevSel = prevSelectionRef.current[asset.id];
        const justMovedToNewPhase =
          !!previousPhase &&
          previousPhase !== pendingPhase &&
          isPhaseProgression(
            previousPhase as TrialPhaseName,
            pendingPhase as TrialPhaseName,
            TRIAL_PHASES,
          );
        let shouldSelect: boolean;
        if (playerState.time === 0) {
          shouldSelect = false;
        } else if (isFirstPhase(pendingPhase ?? null)) {
          shouldSelect = false;
        } else if (isStartOfGame || justMovedToNewPhase) {
          shouldSelect = true;
        } else {
          shouldSelect = isSelectionActive(prevSel) || prevSel === undefined;
        }
        next[asset.id] = shouldSelect
          ? seedLevels
            ? ("standard" as ActionType)
            : true
          : seedLevels
            ? ("none" as ActionType)
            : false;
        changedAny = true;
      }
      return changedAny ? next : current;
    });
    // --- end classic auto-selection ---

    lastSeenRef.current = snapshot;
  }, [playerState]);

  // Classic AssetsTable change rules, verbatim: status transitions out of
  // development/market, plus forward phase progressions.
  const hasStatusChanged = (asset: AssetSchemaType) => {
    const previousState = prevSnapshot?.states[asset.id];
    return (
      (previousState === "In Development" &&
        (asset.state === "On Market" ||
          asset.state === "Expired" ||
          asset.state === "Failed" ||
          asset.state === "Dropped")) ||
      (previousState === "On Market" &&
        (asset.state === "Expired" ||
          asset.state === "Failed" ||
          asset.state === "Dropped")) ||
      (previousState === "Idle" && asset.state === "Dropped")
    );
  };
  const hasPhaseChanged = (asset: AssetSchemaType) => {
    const previousPhase = prevSnapshot?.phases[asset.id];
    const currentPhase = asset.pending_trial_phase;
    if (previousPhase && currentPhase && previousPhase !== currentPhase) {
      return isPhaseProgression(
        previousPhase as TrialPhaseName,
        currentPhase as TrialPhaseName,
        TRIAL_PHASES,
      );
    }
    return false;
  };
  const hasAnyChange = (asset: AssetSchemaType) =>
    hasStatusChanged(asset) || hasPhaseChanged(asset);
  // Classic StatusChangeDot: three differentiated tooltip messages.
  const changedKind = (
    asset: AssetSchemaType,
  ): "both" | "status" | "phase" | undefined => {
    const status = hasStatusChanged(asset);
    const phase = hasPhaseChanged(asset);
    return status && phase
      ? "both"
      : status
        ? "status"
        : phase
          ? "phase"
          : undefined;
  };

  // New arrivals this turn (classic highlightedAssetIds): amber for
  // organic additions, teal for BD acquisitions.
  const arrivalHighlight = (
    asset: AssetSchemaType,
  ): "changed" | "bd" | undefined => {
    if (!prevSnapshot || prevSnapshot.ids.has(asset.id)) return undefined;
    return asset.type === "BD" ? "bd" : "changed";
  };

  // PTRS reading affordability, classic AssetsTable: the gate spans the
  // whole portfolio's reading spend, never blocking a step *down*.
  const readingCostOf = (asset: AssetSchemaType, count: number): number => {
    if (count <= 0) return 0;
    const costs = asset.ptrs_reading_costs ?? [];
    return costs[count - 1] ?? 0;
  };
  const totalReadingCost = allAssets.reduce(
    (sum, a) => sum + readingCostOf(a, readings[a.id] ?? 0),
    0,
  );
  const readingAffordableUpTo = (asset: AssetSchemaType): number => {
    const count = readings[asset.id] ?? 0;
    const rowCost = readingCostOf(asset, count);
    let affordable = 0;
    const max = asset.ptrs_reading_costs?.length ?? 0;
    for (let k = 1; k <= max; k++) {
      if (totalReadingCost - rowCost + readingCostOf(asset, k) <= (cash ?? 0))
        affordable = k;
      else break;
    }
    return affordable;
  };

  // Asset buckets per tab, from live state.
  const devRows = allAssets
    .filter(
      (asset) => asset.state === "Idle" || asset.state === "In Development",
    )
    .map((asset) => ({
      ...toAssetRow(
        asset,
        asset.state === "In Development" && levelsEnabled
          ? // Levels mode: In Development rows carry a live stop toggle;
            // the selection value drives it ("stop" = abandoning).
            (invests[asset.id] ?? true)
          : (invests[asset.id] ?? false),
        readings[asset.id] ?? 0,
        drops[asset.id] ?? false,
        hasAnyChange(asset),
        arrivalHighlight(asset),
        // Classic parity (legacy mode): In Development continues
        // automatically — the switch is locked on, only drop is valid.
        asset.state === "In Development" && !levelsEnabled,
      ),
      readingAffordableUpTo: readingAffordableUpTo(asset),
      changedKind: changedKind(asset),
    }));
  const marketRows = allAssets
    .filter((asset) => asset.state === "On Market")
    .map((asset) => ({
      ...toAssetRow(asset, false, 0, false, hasAnyChange(asset)),
      changedKind: changedKind(asset),
    }));
  const expiredRows = Object.values(playerState?.expired_assets ?? {}).map(
    (asset) => ({
      ...toAssetRow(asset, false, 0, false, hasAnyChange(asset)),
      changedKind: changedKind(asset),
    }),
  );
  const droppedRows = Object.values(playerState?.dropped_assets ?? {}).map(
    (asset) => ({
      ...toAssetRow(asset, false, 0, false, hasAnyChange(asset)),
      changedKind: changedKind(asset),
    }),
  );
  const tabRows =
    assetTab === "development"
      ? devRows
      : assetTab === "market"
        ? marketRows
        : assetTab === "expired"
          ? expiredRows
          : droppedRows;

  // Idle assets toggled to develop this turn each claim a free site next
  // year (classic pendingSiteIncoming — identical predicate, which counts
  // any value other than off/"none"/"stop").
  const pendingSiteIncoming = playerState?.clinical_sites_enabled
    ? allAssets.filter((a) => {
        if (a.state !== "Idle") return false;
        const val = combinedSelection[a.id];
        return (
          val === true ||
          (typeof val === "string" && val !== "none" && val !== "stop")
        );
      }).length
    : 0;

  // Classic-gated feature panels shared by both modes: TA experience and
  // R&D capacity (classic components reused, like SiteCubes).
  const featureSections: BoardSection[] = [
    ...(playerState?.ta_experience_enabled &&
    playerState.ta_experience &&
    Object.keys(playerState.ta_experience).length > 0
      ? [
          {
            key: "ta",
            title: "TA Experience",
            icon: GraduationCap,
            content: (
              <TAExperience
                taExperience={playerState.ta_experience}
                maxExperience={playerState.experience_to_full_knowledge}
                maxTotalExperience={playerState.max_total_experience}
              />
            ),
          } satisfies BoardSection,
        ]
      : []),
    ...(levelsEnabled &&
    playerState?.capacity_used !== undefined &&
    playerState?.capacity_base !== undefined
      ? [
          {
            key: "capacity",
            title: "R&D Capacity",
            icon: Gauge,
            info: informationDictionary.investmentLevels,
            content: (
              <RDCapacity
                capacityUsed={playerState.capacity_used}
                capacityBase={playerState.capacity_base}
                successModifier={playerState.success_modifier}
                costModifier={playerState.cost_modifier}
              />
            ),
          } satisfies BoardSection,
        ]
      : []),
  ];

  const multiBoardSections: BoardSection[] = [
    {
      key: "sites",
      title: "Clinical Sites",
      icon: FlaskConical,
      info: {
        title: "Clinical Sites — Trial Capacity",
        description: CLINICAL_SITES_INFO,
      },
      badge: playerState?.clinical_sites_enabled
        ? playerState.free_sites
        : undefined,
      content: playerState?.clinical_sites_enabled ? (
        <ClinicalSitesBoard
          operationalSites={playerState.operational_sites}
          sitesOccupied={playerState.sites_occupied}
          freeSites={playerState.free_sites}
          sitesInDevelopment={playerState.sites_in_development}
          nextSitePurchaseCost={playerState.next_site_purchase_cost}
          playerCash={playerState.cash}
          buySite={buySite}
          onBuySiteChange={setBuySite}
          siteAuctionActive={multiState?.site_auction_active ?? false}
          siteBid={siteBid}
          maxSiteBid={siteMaxBid}
          onSiteBidChange={setSiteBid}
          pendingIncoming={pendingSiteIncoming}
        />
      ) : (
        <EmptyState
          icon={Building2}
          message="Clinical sites are not enabled in this game"
        />
      ),
    },
    ...featureSections,
    {
      key: "bd",
      title: "BD Market",
      icon: Handshake,
      info: {
        title: "BD Market — Asset Auctions",
        description: BD_MARKET_INFO,
      },
      badge: multiState?.bd_enabled ? (multiState?.bd_assets.length ?? 0) : 0,
      content: multiState?.bd_enabled ? (
        <BDMarketBoard
          bdAssets={multiState?.bd_assets ?? []}
          playerCash={playerState?.cash ?? 0}
          bdBids={bdBids}
          maxBid={bdMaxBid}
          onBidChange={(index, bid) =>
            setBdBids((prev) => {
              // Pad gaps with 0 so the array never has holes (classic parity).
              const next = [...prev];
              while (next.length <= index) next.push(0);
              next[index] = bid;
              return next;
            })
          }
          ptrsReadingsEnabled={playerState?.ptrs_readings_enabled ?? false}
          ptrsResearch={readings}
          onReadingChange={(assetId, count) =>
            setReadings((prev) => ({ ...prev, [assetId]: count }))
          }
        />
      ) : (
        <EmptyState
          icon={Handshake}
          message="The BD market is not enabled in this game"
        />
      ),
    },
    {
      key: "sales",
      title: "Sales Market",
      icon: LineChart,
      info: { title: "Sales Market", description: SALES_MARKET_INFO },
      badge: (multiState?.indication_markets ?? []).filter((m) =>
        Object.values(m.active_drugs).some((count) => count > 0),
      ).length,
      content: (
        <SalesMarketBoard
          indicationMarkets={multiState?.indication_markets ?? []}
          playerAgentName={multiState?.player_agent_name || "pharma_0"}
        />
      ),
    },
    {
      key: "ci",
      title: "Competitive Intelligence",
      icon: Radar,
      badge: multiState
        ? multiState.alerts.filter(
            (a) => a.agent_id !== multiState.player_agent_name,
          ).length
        : undefined,
      info: {
        title: "Competitive Intelligence",
        description: ALERTS_INFO,
      },
      content: (
        <IntelligenceBoard
          alerts={multiState?.alerts ?? []}
          playerAgentName={multiState?.player_agent_name || "pharma_0"}
        />
      ),
    },
    {
      key: "demand",
      title: "Demand Creation",
      icon: Megaphone,
      info: {
        title: "Demand Creation",
        description: DEMAND_CREATION_INFO,
      },
      badge: Object.values(demandCreation).filter((v) => v === 1).length,
      content: playerState?.marketing_enabled ? (
        <DemandCreationBoard
          indicationMarkets={multiState?.indication_markets ?? []}
          demandCreation={demandCreation}
          onToggle={(key) =>
            setDemandCreation((prev) => {
              const next = { ...prev };
              if (next[key] === 1) delete next[key];
              else next[key] = 1;
              return next;
            })
          }
          dcCost={multiState?.dc_cost ?? 0}
          playerCash={playerState?.cash ?? 0}
        />
      ) : (
        <EmptyState
          icon={Megaphone}
          message="Marketing is not enabled in this game"
        />
      ),
    },
    {
      key: "brand",
      title: "Brand Equity",
      icon: Sparkles,
      info: { title: "Brand Equity", description: BRAND_EQUITY_INFO },
      badge: Object.values(brandEquity).filter((v) => v === 1).length,
      content: playerState?.marketing_enabled ? (
        <BrandEquityBoard
          assets={allAssets}
          brandEquity={brandEquity}
          onToggle={(assetId) =>
            setBrandEquity((prev) => {
              const next = { ...prev };
              if (next[assetId] === 1) delete next[assetId];
              else next[assetId] = 1;
              return next;
            })
          }
          playerCash={playerState?.cash ?? 0}
        />
      ) : (
        <EmptyState
          icon={Sparkles}
          message="Marketing is not enabled in this game"
        />
      ),
    },
  ];

  // Single-player boards (classic Action layout): TA experience, R&D
  // capacity and the AI-hint shop — no shared-market boards.
  const singleBoardSections: BoardSection[] = [
    ...featureSections,
    {
      key: "hints",
      title: "AI Hints",
      icon: Lightbulb,
      content: playerState ? (
        <UnlockHint
          gameId={playerState.id}
          onHintReceived={(newHints, agentName) => {
            setHints(newHints);
            setSelectedAgentName(agentName);
            setHintColumnVisible(true);
          }}
          onHintToggled={(visible, agentName) => {
            setHintColumnVisible(visible);
            if (visible && agentName) {
              setSelectedAgentName(agentName);
            } else {
              setHints({});
              setSelectedAgentName("");
            }
          }}
          onCashDeducted={(amount) => setHintCosts((prev) => prev + amount)}
          currentCash={effectiveCash ?? 0}
          resetKey={playerState.time}
          assets={playerState.assets}
        />
      ) : (
        <EmptyState icon={Lightbulb} message="No game in progress" />
      ),
    },
  ];

  const baseBoardSections =
    mode === "multi" ? multiBoardSections : singleBoardSections;

  // Projection charts: identical data pipeline to the classic ActionChart
  // (processAssetDataForChart + calculateChartYAxisMax from lib/game-data).
  const projection = (dataType: "cost" | "revenue") => {
    if (!playerState) return { series: [] as ProjectionSeries[], yMax: 10 };
    try {
      const processed = processAssetDataForChart({
        assets: allAssets,
        selection: combinedSelection,
        horizon: playerState.horizon,
        dataType,
        currentTime: playerState.time,
        gameState: playerState,
        hintCosts:
          dataType === "cost"
            ? mode === "single"
              ? // Classic single: purchased AI hints + drop fees.
                hintCosts + dropFeesTotal
              : marketingSpendThisYear +
                readingsSpendThisYear +
                bdBidsTotal +
                dropFeesTotal
            : 0,
      });
      const series: ProjectionSeries[] = processed.map((assetSeries) => {
        const values = new Array(playerState.horizon + 1).fill(0);
        assetSeries.forEach((point) => {
          values[point.time] = point.value;
        });
        return {
          id: assetSeries[0]?.assetId ?? "",
          name: assetSeries[0]?.assetName ?? "",
          selected: !!assetSeries[0]?.isSelected,
          values,
        };
      });
      const yMax = calculateChartYAxisMax({
        assets: allAssets,
        horizon: playerState.horizon,
        dataType,
        currentTime: playerState.time,
        gameState: playerState,
        bufferPercentage: 0.2,
        minDomain: 10,
      });
      return { series, yMax };
    } catch (err) {
      console.error("Failed to build projection data:", err);
      return { series: [] as ProjectionSeries[], yMax: 10 };
    }
  };
  const costProjection = projection("cost");
  const budgetProjection = projection("revenue");

  // --- charts, shared by the dashboard row, the focus-view board and the
  // focus-view mini strip (compact = header + sparkline, no axes) ---
  const capitalChartEl = (height: number, compact = false) =>
    playerState ? (
      <CapitalChart
        series={playerState.capital_over_time}
        currentTime={playerState.time}
        // Classic single-player deducts hint spend from the
        // displayed capital (0 in multi).
        currentCapital={playerState.cash - hintCosts}
        totalTime={playerState.horizon}
        height={height}
        compact={compact}
      />
    ) : null;

  const capitalPanel = (height: number) => (
    <div className="relative min-w-0 overflow-hidden rounded bg-secondary/25 p-4">
      <InfoHint
        {...informationDictionary.capitalPlot}
        className="absolute right-3 top-3 z-10"
      />
      {capitalChartEl(height)}
    </div>
  );

  const costChartEl = (height: number, compact = false) => (
    <ProjectionChart
      title="Total Cost this year:"
      axisLabel="Expected Cost"
      info={informationDictionary.costCurve}
      series={costProjection.series}
      horizon={playerState?.horizon ?? 100}
      currentTime={playerState?.time ?? 0}
      yAxisMax={costProjection.yMax}
      height={height}
      compact={compact}
    />
  );
  const budgetChartEl = (height: number, compact = false) => (
    <ProjectionChart
      title="Budget next year:"
      axisLabel="Expected Budget"
      info={informationDictionary.revenueCurve}
      series={budgetProjection.series}
      horizon={playerState?.horizon ?? 100}
      currentTime={playerState?.time ?? 0}
      yAxisMax={budgetProjection.yMax}
      height={height}
      compact={compact}
    />
  );

  // Focus view trades the chart grid for table height — this thin strip
  // keeps all three traces glanceable, and clicking one opens the
  // full-size version in the Charts board.
  const openCharts = () => {
    setLeaderboardOpen(false);
    setActiveBoard("charts");
    setBoardsOpen(true);
  };
  const miniChartRow = (
    <div className="grid grid-cols-3 gap-3">
      {[
        capitalChartEl(44, true),
        costChartEl(44, true),
        budgetChartEl(44, true),
      ].map((chart, i) => (
        <button
          key={i}
          type="button"
          onClick={openCharts}
          aria-label="Open charts board"
          className="min-w-0 overflow-hidden rounded bg-secondary/25 px-3 py-2 text-left transition-colors hover:bg-secondary/50"
        >
          {chart}
        </button>
      ))}
    </div>
  );

  // Focus view hands the whole dashboard row to the table, so the charts
  // move into the boards panel as their own section, first in the list
  // (above Clinical Sites) and first in the rail.
  const boardSections: BoardSection[] = focusView
    ? [
        {
          key: "charts",
          title: "Charts",
          icon: LineChart,
          // Three stacked charts overflow the standard 400px section
          // scroller — let the panel body scroll them instead.
          fullHeight: true,
          content: (
            <div className="space-y-4">
              {capitalPanel(150)}
              <div className="overflow-hidden rounded bg-secondary/25 p-4">
                {costChartEl(150)}
              </div>
              <div className="overflow-hidden rounded bg-secondary/25 p-4">
                {budgetChartEl(150)}
              </div>
            </div>
          ),
        },
        ...baseBoardSections,
      ]
    : baseBoardSections;

  // Results open automatically the moment the game ends.
  useEffect(() => {
    if (gameEnded) setShowResults(true);
  }, [gameEnded]);

  // First-time players get the tour on their own, once the first turn has
  // rendered so every anchor exists. The cookie in useCustomNextStep keeps
  // it to once per player; the ? button replays it on demand.
  const autoTourRef = useRef(false);
  // A boolean, not playerState itself: the first turn sets state more than
  // once, and every re-run of this effect would cancel the pending timer
  // and then bail on the ref, so the tour never opened. Strict mode's
  // double-invoke did the same. The ref is claimed when the timer fires,
  // not when it's scheduled, so a re-run reschedules instead of losing it.
  const tourReady = Boolean(playerState) && !gameEnded;
  useEffect(() => {
    if (!tourReady || autoTourRef.current) return;
    const id = window.setTimeout(() => {
      if (autoTourRef.current) return;
      autoTourRef.current = true;
      startTourIfNotSkipped(tourName, startNextStep);
    }, 400);
    return () => window.clearTimeout(id);
  }, [tourReady, startTourIfNotSkipped, startNextStep, tourName]);

  // The results dialog owns the screen at the end — don't leave a tour
  // overlay cutting a hole in it.
  useEffect(() => {
    if (gameEnded) closeNextStep();
  }, [gameEnded, closeNextStep]);

  // Classic behavior: Dropped tab disappears when empty; don't strand the view.
  useEffect(() => {
    if (assetTab === "dropped" && droppedRows.length === 0) {
      setAssetTab("development");
    }
  }, [assetTab, droppedRows.length]);

  // Final standings, classic MultiAgentGameOver rules: solvent players
  // rank above bankrupt ones, then by net cash flow.
  const standings: Standing[] = multiState
    ? [
        {
          name: multiState.player_agent_name || "You",
          isPlayer: true,
          netCashFlow: multiState.player_cumulative_reward,
          enpv: expectedNPV,
          bankrupt: playerBankrupt,
        },
        ...multiState.opponents.map((opponent) => ({
          name: opponent.display_name,
          agentType: opponent.agent_type,
          netCashFlow: opponent.cumulative_reward,
          enpv: opponent.enpv,
          bankrupt:
            opponent.game_ended &&
            !(opponent.ended_reason ?? "").includes("horizon"),
        })),
      ].sort((a, b) => {
        if (!!a.bankrupt !== !!b.bankrupt) return a.bankrupt ? 1 : -1;
        return b.netCashFlow - a.netCashFlow;
      })
    : [];

  const finalStats: StatProps[] = [
    {
      label: "Final Capital",
      value: cash !== undefined ? `£${formatDisplayNumber(cash)}` : "—",
      size: "lg",
    },
    {
      label: "eNPV",
      value: enpv !== undefined ? `£${formatDisplayNumber(enpv)}` : "—",
      info: informationDictionary.eNPV,
    },
    {
      label: "eROI",
      value: eroi !== undefined ? `x${eroi.toFixed(1)}` : "—",
      info: informationDictionary.eROI,
    },
  ];

  // --- shared layout pieces (used by both the v1 and v2 arrangements) ---
  const railColumn = (className: string) => (
    <div id="v2-tour-rail" className={className}>
      <RailButton
        icon={boardsOpen ? PanelRightClose : PanelRightOpen}
        label={boardsOpen ? "Close boards" : "Open boards"}
        onClick={() => {
          setLeaderboardOpen(false);
          setBoardsOpen((prev) => !prev);
        }}
      />
      {boardSections.map((section) => (
        <RailButton
          key={section.key}
          icon={section.icon}
          label={section.title}
          active={boardsOpen && activeBoard === section.key}
          badge={section.badge}
          onClick={() => {
            setActiveBoard(section.key);
            setLeaderboardOpen(false);
            setBoardsOpen(true);
          }}
        />
      ))}

      {/* Leaderboard gets its own panel. Multiplayer only — single has
          no standings. The full dashboard anchors it at the bottom; the
          shorter focus rail keeps it with the rest of the icons. */}
      {mode === "multi" && (
        <div
          id="v2-tour-leaderboard"
          className={focusView ? undefined : "mt-auto"}
        >
          <RailButton
            icon={Trophy}
            label="Leaderboard"
            active={leaderboardOpen}
            onClick={() => {
              setBoardsOpen(false);
              setLeaderboardOpen((prev) => !prev);
            }}
          />
        </div>
      )}
    </div>
  );

  const assetTabs: AssetTab[] = [
    {
      key: "development",
      label: "In Development",
      count: devRows.length,
      dot: devRows.some((row) => row.changed),
    },
    {
      key: "market",
      label: "On Market",
      count: marketRows.length,
      dot: marketRows.some((row) => row.changed),
    },
    {
      key: "expired",
      label: "Expired/Failed",
      count: expiredRows.length,
      dot: expiredRows.some((row) => row.changed),
    },
    ...(droppedRows.length > 0
      ? [
          {
            key: "dropped" as const,
            label: "Dropped",
            count: droppedRows.length,
            dot: droppedRows.some((row) => row.changed),
          },
        ]
      : []),
  ];

  const assetTableEl = (
    <AssetTable
      tabs={assetTabs}
      // Focus view: tab strip + legend live under the stats block instead;
      // the legend filter is driven externally there.
      externalTabs={focusView}
      highlightFilter={focusView ? tableFilter : null}
      // Focus view gives the table the rest of the viewport: everything
      // above it (top bar + stats/tabs row + sparkline strip + padding) is
      // a fixed ~300px, with a floor so short windows still scroll sanely.
      scrollMaxHeight={
        focusView ? "max-h-[max(420px,calc(100dvh-300px))]" : undefined
      }
      activeTab={assetTab}
      onTabChange={setAssetTab}
      // Focus view renders the tab strip itself, so the tabs anchor moves
      // out there with it; the header and first-row anchors stay on the
      // table. They are deliberately thin strips rather than the whole
      // table — the tour card is positioned outside whatever it highlights
      // and gets clipped at the viewport edge, so a full-height anchor
      // leaves nowhere for the card to go.
      tourIds={{
        tabs: focusView ? undefined : "v2-tour-tabs",
        header: "v2-tour-table",
        firstRow: "v2-tour-row",
      }}
      rows={tabRows}
      onToggleInvest={(id, invest) =>
        setInvests((prev) => ({
          ...prev,
          // Levels mode: the switch maps to standard/none (classic
          // handleAssetSelection); legacy mode stays boolean.
          [id]: levelsEnabled ? (invest ? "standard" : "none") : invest,
        }))
      }
      onLevelChange={(id, level) =>
        setInvests((prev) => ({ ...prev, [id]: level }))
      }
      onDrop={(id) => {
        // Toggle drop; dropping clears any invest selection.
        setDrops((prev) => ({ ...prev, [id]: !prev[id] }));
        setInvests((prev) => ({
          ...prev,
          [id]: levelsEnabled ? "none" : false,
        }));
      }}
      // Classic single-player shows PTRS "eff" but has no reading
      // purchases — omitting the handler hides the selector.
      onReadingsChange={
        mode === "multi"
          ? (id, count) => setReadings((prev) => ({ ...prev, [id]: count }))
          : undefined
      }
      hints={hints}
      hintColumnVisible={hintColumnVisible}
      selectedAgentName={selectedAgentName}
      investmentLevelsEnabled={levelsEnabled}
      distributionalPtrsEnabled={
        playerState?.distributional_ptrs_enabled ?? false
      }
      interimObservationsEnabled={
        playerState?.interim_observations_enabled ?? false
      }
      emphasizeCashValue={mode === "multi"}
      ptrsReadingsEnabled={playerState?.ptrs_readings_enabled ?? false}
      reinvestmentPercentage={playerState?.reinvestment_percentage}
    />
  );
  // --- end shared layout pieces ---

  return (
    <div className="relative -mb-4 -mt-6 flex h-dvh overflow-hidden font-light">
      <div className="v2-scroll min-w-0 flex-1 overflow-y-auto">
        <GameTopBar
          year={year}
          totalYears={totalYears}
          onHome={onExit}
          onRestart={onRestart}
          onTour={startTour}
          onNextYear={handleNextYear}
          advancing={advancing}
          agentsDeciding={mode === "multi" && !agentsReady}
          bankrupt={playerBankrupt}
          gameEnded={gameEnded}
          onViewResults={() => setShowResults(true)}
          focusView={focusView}
          onFocusViewChange={handleFocusViewChange}
          // Focus view: rank + net cash flow live in the top bar (the
          // standings grid below is removed — the leaderboard panel
          // carries the full picture).
          rank={focusView ? rank : undefined}
          netCashFlow={focusView ? netCashFlow : undefined}
        />

        {/* End-of-game results */}
        <GameOverDialog
          open={showResults}
          onOpenChange={setShowResults}
          // Classic reports the years actually played, not the horizon —
          // early endings (bankruptcy) say the real length.
          totalYears={playerState?.time ?? totalYears}
          standings={standings}
          playerStats={finalStats}
          onPlayAgain={() => {
            setShowResults(false);
            onRestart();
          }}
          onRestartSame={
            onRestartSameGame
              ? () => {
                  setShowResults(false);
                  onRestartSameGame();
                }
              : undefined
          }
          onHome={onExit}
        />

        {/* All competitors, on demand */}
        <Dialog open={showAllCompetitors} onOpenChange={setShowAllCompetitors}>
          <DialogContent className="max-w-lg rounded">
            <DialogHeader>
              <DialogTitle className="font-bold">Competitors</DialogTitle>
            </DialogHeader>
            <div className="space-y-2">
              {standingCards.map((standing) => (
                <CompetitorCard key={standing.name} {...standing} />
              ))}
            </div>
          </DialogContent>
        </Dialog>

        {/* Sections get built one at a time via /design */}
        <div className="mx-auto max-w-[1560px] space-y-4 p-4">
          {playerBankrupt && !gameEnded && (
            <div className="rounded bg-destructive/5 px-3 py-1.5 text-sm text-destructive">
              You are bankrupt — the remaining years play out automatically
              while your competitors finish the game.
            </div>
          )}
          {/* Classic kept the sites panel permanently on screen, so a
              sealed-bid auction year was always visible. The v2 board is
              docked — surface auction years with a banner instead. */}
          {multiState?.site_auction_active &&
            !(boardsOpen && activeBoard === "sites") &&
            !gameEnded && (
              <div className="flex items-center justify-between gap-3 rounded bg-gradient-to-r from-[#fff3cd] to-[#fffaf0] px-3 py-2 text-sm text-[#8a6d00]">
                <span className="flex items-center gap-2">
                  <Bell className="size-4 shrink-0" />
                  <span>
                    <span className="font-bold">
                      Clinical site auction this year
                    </span>{" "}
                    — place a sealed bid before advancing; the highest bid wins
                    the site.
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setActiveBoard("sites");
                    setBoardsOpen(true);
                  }}
                  className="shrink-0 rounded-full bg-card px-3 py-1 text-xs font-bold text-[#8a6d00] hover:bg-[#fff7e0]"
                >
                  Place a bid
                </button>
              </div>
            )}
          {error && (
            <div className="rounded bg-destructive/5 px-3 py-1.5 text-sm text-destructive">
              <div className="flex items-start gap-2">
                <TriangleAlert className="mt-[3px] size-4 shrink-0" />
                <span>{error}</span>
              </div>
            </div>
          )}
          {focusView ? (
            /* Focus view: one header row (stats + tabs) and one thin
               sparkline strip above the table, so the table gets the
               rest of the viewport; the rail spans all three rows. */
            <div className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2">
              {/* One header row: stats on the left, the table's legend +
                  tab strip pulled out of the table and pinned to the row
                  bottom on the right, so the table starts immediately. */}
              <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-8 gap-y-3 px-2 pt-2">
                <StatGroup id="v2-tour-stats" stats={stats} />
                <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-2">
                  <AssetLegend
                    counts={{
                      changed: tabRows.filter(
                        (row) => row.highlight === "changed",
                      ).length,
                      bd: tabRows.filter((row) => row.highlight === "bd")
                        .length,
                    }}
                    active={tableFilter}
                    onToggle={(key) =>
                      setTableFilter((prev) => (prev === key ? null : key))
                    }
                  />
                  <AssetTabsBar
                    id="v2-tour-tabs"
                    tabs={assetTabs}
                    activeTab={assetTab}
                    onTabChange={(key) => {
                      setAssetTab(key);
                      // Filter is per-tab context; reset on switch.
                      setTableFilter(null);
                    }}
                  />
                </div>
              </div>
              {railColumn("row-span-3 flex w-12 flex-col gap-2")}
              {/* Thin strip of sparklines: the charts stay present at a
                  glance without costing the table a chart-sized row. */}
              <div id="v2-tour-charts" className="min-w-0">
                {miniChartRow}
              </div>
              <div className="min-w-0">{assetTableEl}</div>
            </div>
          ) : (
            <>
              {/* Structure scaffold — boxes only until the layout is agreed.
            Top row: 40% | 60% | icon rail (panel/board launchers).
            Bottom row: the table — the main focus, gets the space. */}
              {/* Shared grid: row heights are common across both columns so the
            horizontal seams align symmetrically. */}
              <div className="grid grid-cols-[2fr_3fr_auto] gap-4">
                <div className="flex min-w-0 flex-col justify-center gap-6 p-2">
                  {/* clean stats row */}
                  <StatGroup id="v2-tour-stats" stats={stats} />

                  {/* standings: rank + net cash flow sit inline with the
                  heading (they used to be a tile beside the competitor card,
                  which wrapped to a second row under ~1260px), then one full
                  -width competitor card. Full dashboard only — in focus view
                  rank/NCF live in the top bar and the leaderboard panel
                  covers the standings. */}
                  {multiState && (
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                        <h3 className="text-sm font-bold tracking-wide">
                          Standings
                        </h3>
                        {rank !== undefined && (
                          <>
                            <span className="text-muted-foreground">
                              Your rank
                            </span>
                            <RankBadge rank={rank} />
                            <span className="text-muted-foreground/30">·</span>
                            <span className="text-muted-foreground">
                              Net Cash Flow
                            </span>
                            <span
                              className={cn(
                                "font-bold tabular-nums",
                                multiState.player_cumulative_reward < 0 &&
                                  "text-destructive",
                              )}
                            >
                              {formatDisplayNumber(
                                multiState.player_cumulative_reward,
                              )}
                            </span>
                          </>
                        )}
                        {competitors.length > 1 && (
                          <button
                            onClick={() => {
                              setBoardsOpen(false);
                              setLeaderboardOpen(true);
                            }}
                            className="ml-auto text-primary hover:underline"
                          >
                            See all {standingCards.length}
                          </button>
                        )}
                      </div>
                      {competitors[0] && <CompetitorCard {...competitors[0]} />}
                    </div>
                  )}
                </div>
                {/* row 1, col 2 */}
                <div
                  id="v2-tour-charts"
                  className="min-w-0 overflow-hidden rounded bg-secondary/25 p-4"
                >
                  {costChartEl(190)}
                </div>

                {/* col 3: board launchers, fixed in place; they drive the panel */}
                {railColumn("row-span-2 flex w-12 flex-col gap-2")}

                {/* row 2, col 1 */}
                {capitalPanel(210)}

                {/* row 2, col 2 */}
                <div className="min-w-0 overflow-hidden rounded bg-secondary/25 p-4">
                  {budgetChartEl(190)}
                </div>
              </div>
              {assetTableEl}
            </>
          )}
        </div>
      </div>

      {/* Boards panel: docks beside the dashboard at 2xl+, slides over it below that */}
      <BoardsPanel
        open={boardsOpen}
        onClose={() => setBoardsOpen(false)}
        sections={boardSections}
        activeSection={activeBoard}
        onActiveSectionChange={setActiveBoard}
      />

      {/* Dedicated leaderboard panel */}
      <LeaderboardPanel
        open={leaderboardOpen}
        onClose={() => setLeaderboardOpen(false)}
        standings={standingCards}
      />
    </div>
  );
}
