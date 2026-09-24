"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDisplayNumber } from "@/lib/numbers";
import { EmptyState } from "./EmptyState";
import {
  FlaskConical,
  LineChart,
  Archive,
  Trash2 as TrashIcon,
} from "lucide-react";
import AssetDetailDialog from "./AssetDetailDialog";
import { InfoHint } from "./InfoHint";
import { informationDictionary } from "@/lib/information-dictionary-game";
import { CircleCheck, StopCircle, TriangleAlert } from "lucide-react";
import AssetHintYes from "@/components/InvestmentGame/AssetHintYes";
import AssetHintNo from "@/components/InvestmentGame/AssetHintNo";
import type { ActionType, AssetSchemaType } from "@/lib/definitionsGameZ";

/**
 * v2 asset table — the main surface of the game screen. Hairline grid,
 * muted headers, generous cell padding. Scrolls both ways inside its
 * frame: the header sticks vertically, the controls + asset columns
 * stick horizontally (opaque backgrounds so content passes underneath).
 * Purely presentational; all actions come in as callbacks.
 */

export type AssetTabKey = "development" | "market" | "expired" | "dropped";

export interface AssetRow {
  id: string;
  name: string;
  ta: string;
  indication: string;
  phase: string;
  costThisYear: number;
  ptrs: number;
  ptrsEff: number;
  readings: number;
  readingsFree: boolean;
  /** Cost of buying 1..N readings this year (drives the dropdown). */
  readingCosts?: number[];
  remainingPhaseCost: number;
  remainingPhaseTime: number;
  cashEnpv: number;
  eroi: number;
  pys: number;
  timeToExpiry: number;
  /** Distributional PTRS extras (fractions, formatted in the cell). */
  ptrsRangeLow?: number;
  ptrsRangeHigh?: number;
  ptrsConfidence?: number;
  /** Interim trial signal (In Development only; "na" for other states). */
  interim?: "positive" | "negative" | "pending" | "na";
  /** Highest reading count still affordable given the rest of the portfolio. */
  readingAffordableUpTo?: number;
  /** On Market extras. */
  revenueThisStep?: number;
  timeToPys?: number;
  timeOnMarket?: number;
  /** Full (business) eNPV — shown instead of Cash eNPV in single-player. */
  businessEnpv?: number;
  invest: boolean;
  /** Selection value as an investment level (levels mode). */
  level?: string;
  /** "stop" selected this turn (levels mode: asset will be abandoned). */
  stopping?: boolean;
  /** The asset's live investment level (levels mode, In Development). */
  currentLevel?: string | null;
  /** Backend marks this asset droppable (drop_action feature). */
  dropAvailable?: boolean;
  /** Cash fee for dropping (25% of remaining phase cost; 0 on market). */
  dropFee?: number;
  /** Asset is In Development (levels mode renders a live stop toggle). */
  inDevelopment?: boolean;
  /**
   * In Development, legacy mode: investment continues automatically, so
   * the switch is locked on (classic parity) — dropping is the only
   * valid action.
   */
  locked?: boolean;
  /** Marked for voluntary drop this turn (mutually exclusive with invest). */
  dropped?: boolean;
  /** Status/phase changed since last year (teal dot next to the name). */
  changed?: boolean;
  /** What changed — drives the classic differentiated dot tooltips. */
  changedKind?: "both" | "status" | "phase";
  /** Arrived this year: organically ("changed") or via BD ("bd"). */
  highlight?: "changed" | "bd";
  /** Full asset for the classic detail dialog behind the info icon. */
  infoAsset?: AssetSchemaType;
}

const CONTROLS_WIDTH = 104;

const TH =
  "sticky top-0 z-20 bg-card px-4 py-3 text-left text-xs font-medium tracking-wide text-muted-foreground whitespace-nowrap border-b border-foreground/10";
const TH_NUM = cn(TH, "text-right");
const TD = "px-4 py-3.5 text-sm align-middle whitespace-nowrap";
const TD_NUM = cn(TD, "text-right tabular-nums");

// Row tints per variant: the panel variant (replay) uses softer shades —
// there whole tables can be highlighted at once, so full-strength tints
// read loud. Keys: which tint bucket a row falls into.
type TintKey = "dropped" | "invest" | "changed" | "bd" | "none";

const tintKey = (row: AssetRow): TintKey =>
  row.dropped
    ? "dropped"
    : row.invest
      ? "invest"
      : row.highlight === "changed"
        ? "changed"
        : row.highlight === "bd"
          ? "bd"
          : "none";

const ROW_TINTS: Record<"default" | "panel", Record<TintKey, string>> = {
  default: {
    dropped: "bg-gradient-to-r from-[#fdf1f0] via-[#fdf6f5] to-transparent",
    invest: "bg-gradient-to-r from-[#eef4fc] via-[#f4f8fd] to-transparent",
    changed: "bg-gradient-to-r from-[#fff7e0] via-[#fffaf0] to-transparent",
    bd: "bg-gradient-to-r from-[#dff4f8] via-[#f0fafc] to-transparent",
    none: "hover:bg-secondary/30",
  },
  panel: {
    dropped: "bg-gradient-to-r from-[#fdf6f5] via-[#fefbfa] to-transparent",
    invest: "bg-gradient-to-r from-[#f4f8fd] via-[#f9fbfe] to-transparent",
    changed: "bg-gradient-to-r from-[#fffaf0] via-[#fffdf7] to-transparent",
    bd: "bg-gradient-to-r from-[#f0fafc] via-[#f7fcfd] to-transparent",
    none: "hover:bg-secondary/30",
  },
};

// Sticky column backgrounds must be opaque or scrolling content shows
// through; hover/invest shades are solid equivalents of the row tints.
const STICKY_TINTS: Record<"default" | "panel", Record<TintKey, string>> = {
  default: {
    dropped: "bg-[#fdf1f0] group-hover:bg-[#fbeae8]",
    invest: "bg-[#eef4fc] group-hover:bg-[#e9f0fa]",
    changed: "bg-[#fff7e0] group-hover:bg-[#faf0d2]",
    bd: "bg-[#dff4f8] group-hover:bg-[#d3eef4]",
    none: "bg-card group-hover:bg-[#f4f5f6]",
  },
  panel: {
    dropped: "bg-[#fdf6f5] group-hover:bg-[#fbeeec]",
    invest: "bg-[#f4f8fd] group-hover:bg-[#edf3fb]",
    changed: "bg-[#fffaf0] group-hover:bg-[#fdf4de]",
    bd: "bg-[#f0fafc] group-hover:bg-[#e2f3f8]",
    none: "bg-card group-hover:bg-[#f4f5f6]",
  },
};

/** Active legend filter: show only rows with this arrival highlight. */
export type HighlightFilter = "changed" | "bd" | null;

export interface AssetTab {
  key: AssetTabKey;
  label: string;
  count: number;
  dot?: boolean;
}

/**
 * The table's tab strip — normally rendered by AssetTable itself, but
 * exported so a layout can place it elsewhere (externalTabs mode).
 */
export function AssetTabsBar({
  tabs,
  activeTab,
  onTabChange,
  background = true,
  className,
  id,
}: {
  tabs: AssetTab[];
  activeTab: AssetTabKey;
  onTabChange: (key: AssetTabKey) => void;
  /** Grey strip behind the tabs (off inside grey panels). */
  background?: boolean;
  className?: string;
  /** Anchor for the onboarding tour. */
  id?: string;
}) {
  return (
    <div
      id={id}
      className={cn(
        "inline-flex w-fit items-center gap-0.5 rounded",
        background && "bg-secondary/60 p-1",
        className,
      )}
    >
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          className={cn(
            "relative rounded px-2.5 py-1 text-xs transition-colors",
            tab.key === activeTab
              ? "bg-card font-bold text-primary shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.label}{" "}
          <span
            className={cn(
              "tabular-nums",
              tab.key === activeTab
                ? "text-primary/60"
                : "text-muted-foreground/60",
            )}
          >
            ({tab.count})
          </span>
          {tab.dot && (
            <span
              title="Recent changes"
              className="absolute right-1 top-1 size-1.5 rounded-full bg-[#1ca8c0]"
            />
          )}
        </button>
      ))}
    </div>
  );
}

function LegendSwatch({
  className,
  label,
  count,
  active,
  onClick,
}: {
  className: string;
  label: string;
  count?: number;
  active?: boolean;
  onClick?: () => void;
}) {
  const body = (
    <>
      <span className={cn("inline-block size-3", className)} />
      {label}
      {count !== undefined && <span className="tabular-nums">({count})</span>}
    </>
  );
  if (!onClick) {
    return <span className="flex items-center gap-1.5">{body}</span>;
  }
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={count === 0 && !active}
      className={cn(
        // No dimming at zero — an empty bucket just stops being clickable;
        // fading it read as washed out.
        "-my-1 flex items-center gap-1.5 rounded-full px-2 py-1 transition-colors",
        active
          ? "bg-secondary/70 font-bold text-foreground"
          : count === 0
            ? "cursor-default"
            : "hover:bg-secondary/50 hover:text-foreground",
      )}
    >
      {body}
    </button>
  );
}

/** Row-tint legend; rendered inside the default table header row, or
 * standalone (e.g. once above several replay tables). `extended` adds
 * the invest/drop tints — needed where the tables have no controls.
 * With `counts`/`onToggle` the entries become filter toggles. */
export function AssetLegend({
  extended = false,
  counts,
  active = null,
  onToggle,
  className,
}: {
  extended?: boolean;
  /** Row counts per highlight; shown after the labels. */
  counts?: { changed: number; bd: number };
  /** Currently active filter (when the legend is interactive). */
  active?: HighlightFilter;
  /** Makes the entries clickable filter toggles. */
  onToggle?: (key: "changed" | "bd") => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-4 text-xs text-muted-foreground",
        className,
      )}
    >
      {extended && (
        <>
          <LegendSwatch
            className="bg-gradient-to-r from-[#c9dbf5] to-[#eef4fc]"
            label="Investing"
          />
          <LegendSwatch
            className="bg-gradient-to-r from-[#f6cdc8] to-[#fdf1f0]"
            label="Dropped"
          />
        </>
      )}
      <LegendSwatch
        className="bg-gradient-to-r from-[#ffedb3] to-[#fff7e0]"
        label="New / Changed"
        count={counts?.changed}
        active={active === "changed"}
        onClick={onToggle && (() => onToggle("changed"))}
      />
      <LegendSwatch
        className="bg-gradient-to-r from-[#bfe9f2] to-[#dff4f8]"
        label="BD Acquisition"
        count={counts?.bd}
        active={active === "bd"}
        onClick={onToggle && (() => onToggle("bd"))}
      />
    </div>
  );
}

function money(value: number) {
  const formatted = `£${formatDisplayNumber(Math.abs(value))}`;
  return value < 0 ? `-${formatted}` : formatted;
}

export function AssetTable({
  tabs,
  activeTab,
  onTabChange,
  rows,
  onToggleInvest,
  onLevelChange,
  onDrop,
  onReadingsChange,
  investmentLevelsEnabled = false,
  distributionalPtrsEnabled = false,
  interimObservationsEnabled = false,
  emphasizeCashValue = true,
  hints = {},
  hintColumnVisible = false,
  selectedAgentName = "",
  ptrsReadingsEnabled = false,
  reinvestmentPercentage = 1,
  readOnly = false,
  variant = "default",
  highlightFilter = null,
  externalTabs = false,
  scrollMaxHeight = "max-h-[620px]",
  tourIds,
  className,
}: {
  tabs: AssetTab[];
  activeTab: AssetTabKey;
  onTabChange: (key: AssetTabKey) => void;
  rows: AssetRow[];
  onToggleInvest?: (id: string, invest: boolean) => void;
  /** Levels mode: pick an investment level ("minimal" | "standard" | "accelerated" | "stop" | "none"). */
  onLevelChange?: (id: string, level: ActionType) => void;
  onDrop?: (id: string) => void;
  onReadingsChange?: (id: string, readings: number) => void;
  /** Investment-levels feature flag: level dropdowns + live stop toggle. */
  investmentLevelsEnabled?: boolean;
  /** Distributional PTRS: expected value + p10–p90 range + confidence. */
  distributionalPtrsEnabled?: boolean;
  /** Interim trial observations: adds the Interim Signal column. */
  interimObservationsEnabled?: boolean;
  /** Cash eNPV as the value column (multi); false shows full eNPV (single). */
  emphasizeCashValue?: boolean;
  /** Purchased AI hints, keyed by asset id (single-player feature). */
  hints?: Record<string, boolean>;
  /** Shows the Hint column with the advising agent's name. */
  hintColumnVisible?: boolean;
  selectedAgentName?: string;
  /** Passed through to the classic AssetInfo detail dialog. */
  ptrsReadingsEnabled?: boolean;
  reinvestmentPercentage?: number;
  /** Replay/spectator mode: controls reflect state but can't be changed. */
  readOnly?: boolean;
  /**
   * "panel": for tables inside a grey panel — no tab-strip background
   * (the panel provides it) and the legend sits over the table instead
   * of beside the tabs.
   */
  variant?: "default" | "panel";
  /**
   * External highlight filter (panel variant, where the legend lives
   * outside the table). The default variant filters via its own legend.
   */
  highlightFilter?: HighlightFilter;
  /** The layout renders the tab strip itself (via AssetTabsBar). */
  externalTabs?: boolean;
  /** Tailwind max-height for the scroll frame; layouts that own the
   * viewport (focus view) pass a dvh calc instead of the fixed cap. */
  scrollMaxHeight?: string;
  /**
   * Anchors for the onboarding tour. Opt-in per call site because the
   * replay screen renders several of these tables at once and ids have
   * to stay unique — only the live game table passes them.
   *
   * `header` and `firstRow` land on invisible stand-in overlays rather
   * than the thead and tr themselves; see the bands effect below.
   */
  tourIds?: { tabs?: string; header?: string; firstRow?: string };
  className?: string;
}) {
  const interactive = activeTab === "development";
  const isMarket = activeTab === "market";
  // Levels mode needs room for the per-row level dropdown.
  const controlsWidth = investmentLevelsEnabled ? 200 : CONTROLS_WIDTH;

  // Value column: Cash eNPV in multi (score-relevant), full eNPV in single.
  const valueLabel = emphasizeCashValue ? "Cash eNPV" : "eNPV";
  const valueInfo = emphasizeCashValue
    ? informationDictionary.cashEnpv
    : informationDictionary.eNPV;
  const valueOf = (row: AssetRow) =>
    emphasizeCashValue ? row.cashEnpv : (row.businessEnpv ?? row.cashEnpv);

  const HeadHint = ({
    info,
  }: {
    info: { title: string; description: string };
  }) => (
    <span className="ml-1 inline-flex align-middle">
      <InfoHint {...info} />
    </span>
  );

  // --- identical hint display rules to the classic AssetsTable ---
  const showHintColumn = hintColumnVisible && interactive && !readOnly;
  const hintDisplay = (row: AssetRow) => {
    const hasHint = hints[row.id] !== undefined;
    const hintValue = hints[row.id];
    const isSelected = row.invest;
    const isIdle = !row.inDevelopment;
    if (!hasHint) {
      if (isIdle) {
        return {
          component: <AssetHintNo />,
          className: isSelected ? "" : "opacity-20",
        };
      }
      return null;
    }
    if (hintValue) {
      return {
        component: <AssetHintYes />,
        className: isSelected ? "opacity-60" : "",
      };
    }
    return {
      component: <AssetHintNo />,
      className: !isSelected ? "opacity-60" : "",
    };
  };
  // --- end identical hint rules ---

  // Legend filter: own state when the legend is inline (default variant),
  // externally controlled in the panel variant. Cleared on tab change.
  const [ownFilter, setOwnFilter] = useState<HighlightFilter>(null);
  useEffect(() => setOwnFilter(null), [activeTab]);
  // externalTabs lifts the legend (and its filter) to the layout, so the
  // external highlightFilter prop drives filtering there too.
  const filter =
    variant === "default" && !externalTabs ? ownFilter : highlightFilter;
  const counts = {
    changed: rows.filter((r) => r.highlight === "changed").length,
    bd: rows.filter((r) => r.highlight === "bd").length,
  };
  const displayRows = filter
    ? rows.filter((r) => r.highlight === filter)
    : rows;

  // Panel variant is denser: tighter cell padding (twMerge lets these
  // override the base classes).
  const dense = variant === "panel" && "px-3 py-2.5";
  const th = cn(TH, dense);
  const thNum = cn(TH_NUM, dense);
  const td = cn(TD, dense);
  const tdNum = cn(TD_NUM, dense);
  const assetLeft = interactive ? controlsWidth : 0;

  // Scrollbars are hidden (v2-scroll) — these edge fades hint at
  // remaining content and disappear at the end of the scroll range.
  const scrollRef = useRef<HTMLDivElement>(null);
  const [fade, setFade] = useState({ right: false, bottom: false });
  const updateFade = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setFade({
      right: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
      bottom: el.scrollTop + el.clientHeight < el.scrollHeight - 1,
    });
  }, []);
  useEffect(() => {
    updateFade();
    window.addEventListener("resize", updateFade);
    return () => window.removeEventListener("resize", updateFade);
  }, [updateFade, rows, activeTab, filter]);

  // Tour anchors (see the tourIds prop). The tour spotlight is a hole cut in
  // a page-wide overlay from the target's own bounding box, and the table is
  // min-w-max inside a horizontal scroller — so pointing it at the real thead
  // or tr cuts a hole thousands of pixels wide that runs off the window. The
  // anchors are stand-in overlays instead: they sit in the frame, which is
  // always exactly the visible width, and borrow only the vertical placement
  // of the element they represent.
  const frameRef = useRef<HTMLDivElement>(null);
  const headRef = useRef<HTMLTableSectionElement>(null);
  const firstRowRef = useRef<HTMLTableRowElement>(null);
  type Band = { top: number; height: number } | undefined;
  const [bands, setBands] = useState<{ header: Band; firstRow: Band }>({
    header: undefined,
    firstRow: undefined,
  });
  const anchored = Boolean(tourIds?.header || tourIds?.firstRow);
  useEffect(() => {
    if (!anchored) return;
    const same = (a: Band, b: Band) =>
      a?.top === b?.top && a?.height === b?.height;
    const measure = () => {
      const frame = frameRef.current;
      if (!frame) return;
      const origin = frame.getBoundingClientRect().top;
      const band = (el: Element | null): Band => {
        if (!el) return undefined;
        const rect = el.getBoundingClientRect();
        return { top: rect.top - origin, height: rect.height };
      };
      const next = {
        header: band(headRef.current),
        firstRow: band(firstRowRef.current),
      };
      // Bail on an unchanged measurement: this also runs on scroll, and the
      // table is long enough that a re-render per scroll event is felt.
      setBands((prev) =>
        same(prev.header, next.header) && same(prev.firstRow, next.firstRow)
          ? prev
          : next,
      );
    };
    measure();
    const scroller = scrollRef.current;
    scroller?.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    const observer = new ResizeObserver(measure);
    if (frameRef.current) observer.observe(frameRef.current);
    if (headRef.current) observer.observe(headRef.current);
    if (firstRowRef.current) observer.observe(firstRowRef.current);
    return () => {
      scroller?.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
      observer.disconnect();
    };
  }, [anchored, rows, activeTab, filter]);

  const EMPTY: Record<
    AssetTabKey,
    { icon: typeof FlaskConical; message: string; hint?: string }
  > = {
    development: {
      icon: FlaskConical,
      message: "No assets in development",
      hint: "Acquire assets from the BD market to build your pipeline",
    },
    market: {
      icon: LineChart,
      message: "No drugs on the market yet",
      hint: "Assets reach the market once they clear approval",
    },
    expired: {
      icon: Archive,
      message: "No expired or failed assets",
    },
    dropped: {
      icon: TrashIcon,
      message: "No dropped assets",
    },
  };
  const empty = EMPTY[activeTab];

  return (
    <div className={cn("relative space-y-3", className)}>
      {/* Tabs + legend. With externalTabs the layout renders both the
          tab strip and the legend itself (filter driven via the
          highlightFilter prop), so the table starts immediately. */}
      {!externalTabs && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <AssetTabsBar
            tabs={tabs}
            activeTab={activeTab}
            onTabChange={onTabChange}
            background={variant === "default"}
            id={tourIds?.tabs}
          />
          {variant === "default" && (
            <AssetLegend
              counts={counts}
              active={ownFilter}
              onToggle={(key) =>
                setOwnFilter((prev) => (prev === key ? null : key))
              }
            />
          )}
        </div>
      )}

      {/* Empty tab: quiet empty state instead of a bare table */}
      {rows.length === 0 ? (
        <EmptyState
          icon={empty.icon}
          message={empty.message}
          hint={empty.hint}
        />
      ) : displayRows.length === 0 ? (
        <EmptyState
          message={`No ${filter === "bd" ? "BD acquisition" : "new / changed"} assets in this tab`}
          hint="Clear the legend filter to see all rows"
        />
      ) : (
        <div
          ref={frameRef}
          className="relative overflow-hidden rounded ring-1 ring-foreground/5"
        >
          {/* Stand-in targets for the tour — see the bands effect above.
              Invisible and inert; they exist only to be measured. */}
          {tourIds?.header && bands.header && (
            <div
              id={tourIds.header}
              aria-hidden
              className="pointer-events-none absolute inset-x-0"
              style={bands.header}
            />
          )}
          {tourIds?.firstRow && bands.firstRow && (
            <div
              id={tourIds.firstRow}
              aria-hidden
              className="pointer-events-none absolute inset-x-0"
              style={bands.firstRow}
            />
          )}
          <div
            ref={scrollRef}
            onScroll={updateFade}
            className={cn("v2-scroll overflow-auto bg-card", scrollMaxHeight)}
          >
            <table className="w-full min-w-max border-collapse">
              <thead ref={headRef}>
                <tr>
                  {interactive && (
                    <th
                      className={cn(th, "left-0 z-30")}
                      style={{
                        width: controlsWidth,
                        minWidth: controlsWidth,
                      }}
                    >
                      {investmentLevelsEnabled && (
                        <span className="flex items-center gap-1">
                          Level
                          <InfoHint
                            {...informationDictionary.investmentLevels}
                          />
                        </span>
                      )}
                    </th>
                  )}
                  <th
                    className={cn(th, "z-30 min-w-[140px]")}
                    style={{ left: assetLeft }}
                  >
                    Asset
                  </th>
                  {showHintColumn && (
                    <th className={th}>
                      Hint
                      {selectedAgentName && (
                        <span className="block text-[10px] font-bold text-primary">
                          {selectedAgentName}
                        </span>
                      )}
                    </th>
                  )}
                  <th className={th}>
                    TA
                    <HeadHint info={informationDictionary.TA} />
                  </th>
                  <th className={th}>Indication</th>
                  {isMarket ? (
                    // Classic On Market table: revenue-side columns.
                    <>
                      <th className={thNum}>
                        Budget Next Year
                        <HeadHint info={informationDictionary.budgetNextYear} />
                      </th>
                      <th className={thNum}>
                        {valueLabel}
                        <HeadHint info={valueInfo} />
                      </th>
                      <th className={thNum}>
                        PYS
                        <HeadHint info={informationDictionary.PYS2} />
                      </th>
                      <th className={thNum}>
                        Time to PYS (y)
                        <HeadHint
                          info={informationDictionary.timeFromLaunchToPYS}
                        />
                      </th>
                      <th className={thNum}>Time on Market (y)</th>
                      <th className={thNum}>
                        Expiry (y)
                        <HeadHint info={informationDictionary.timeToExpiry} />
                      </th>
                    </>
                  ) : (
                    <>
                      <th className={th}>Phase</th>
                      <th className={thNum}>Cost This Year</th>
                      <th className={thNum}>
                        PTRS Est. (%)
                        <HeadHint info={informationDictionary.phasePTRS} />
                      </th>
                      {interimObservationsEnabled && (
                        <th className={th}>
                          Interim Signal
                          <HeadHint
                            info={informationDictionary.interimSignal}
                          />
                        </th>
                      )}
                      <th className={thNum}>
                        Remaining Cost
                        <HeadHint
                          info={informationDictionary.remainingPhaseCost}
                        />
                      </th>
                      <th className={thNum}>Remaining Time (y)</th>
                      <th className={thNum}>
                        {valueLabel}
                        <HeadHint info={valueInfo} />
                      </th>
                      <th className={thNum}>eROI</th>
                      <th className={thNum}>
                        PYS
                        <HeadHint info={informationDictionary.PYS} />
                      </th>
                      <th className={thNum}>
                        Expiry (y)
                        <HeadHint info={informationDictionary.timeToExpiry} />
                      </th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row, rowIndex) => (
                  <tr
                    key={row.id}
                    ref={rowIndex === 0 ? firstRowRef : undefined}
                    className={cn(
                      "group border-b border-foreground/5 transition-colors last:border-b-0",
                      ROW_TINTS[variant][tintKey(row)],
                    )}
                  >
                    {interactive && (
                      <td
                        className={cn(
                          TD,
                          "sticky left-0 z-10",
                          STICKY_TINTS[variant][tintKey(row)],
                        )}
                        style={{
                          width: controlsWidth,
                          minWidth: controlsWidth,
                        }}
                      >
                        {investmentLevelsEnabled && !readOnly ? (
                          row.inDevelopment ? (
                            // Levels mode, In Development: live stop toggle
                            // (classic "Abandoning") + current level.
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={!row.stopping}
                                onCheckedChange={(checked) =>
                                  onLevelChange?.(
                                    row.id,
                                    checked ? "standard" : "stop",
                                  )
                                }
                                aria-label={
                                  row.stopping
                                    ? `Resume ${row.name}`
                                    : `Stop ${row.name}`
                                }
                              />
                              {row.stopping ? (
                                <span
                                  title="This asset will be abandoned on the next step and cannot be restarted"
                                  className="flex items-center gap-1 text-xs font-bold text-destructive"
                                >
                                  <StopCircle className="size-3" />
                                  Abandoning
                                </span>
                              ) : (
                                <span className="text-xs capitalize text-muted-foreground">
                                  {row.currentLevel || "standard"}
                                </span>
                              )}
                            </div>
                          ) : (
                            // Levels mode, Idle: invest toggle + level pick.
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={row.invest}
                                onCheckedChange={(checked) =>
                                  onLevelChange?.(
                                    row.id,
                                    checked ? "standard" : "none",
                                  )
                                }
                                aria-label={`Invest in ${row.name}`}
                              />
                              <Select
                                value={
                                  !row.level || row.level === "none"
                                    ? "standard"
                                    : row.level
                                }
                                onValueChange={(value) =>
                                  onLevelChange?.(row.id, value as ActionType)
                                }
                                disabled={!row.invest}
                              >
                                <SelectTrigger
                                  className={cn(
                                    "h-7 w-[110px] border-none bg-secondary/60 text-xs shadow-none",
                                    !row.invest && "opacity-50",
                                  )}
                                >
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="minimal">
                                    Minimal
                                  </SelectItem>
                                  <SelectItem value="standard">
                                    Standard
                                  </SelectItem>
                                  <SelectItem value="accelerated">
                                    Accelerated
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          )
                        ) : (
                          <div>
                            <div className="flex items-center gap-1.5">
                              <Switch
                                checked={row.locked || row.invest}
                                disabled={readOnly || row.dropped || row.locked}
                                onCheckedChange={(checked) =>
                                  onToggleInvest?.(row.id, checked)
                                }
                                aria-label={
                                  row.locked
                                    ? `${row.name} is in development`
                                    : `Invest in ${row.name}`
                                }
                              />
                              {/* Voluntary drop: only when the backend marks
                                  the asset droppable (drop_action feature). */}
                              {!readOnly && row.dropAvailable && (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className={cn(
                                    "size-8",
                                    row.dropped
                                      ? "bg-destructive/10 text-destructive hover:text-destructive"
                                      : "text-muted-foreground hover:text-destructive",
                                  )}
                                  onClick={() => onDrop?.(row.id)}
                                  title={
                                    row.dropped
                                      ? "Undo drop — keep this asset"
                                      : row.dropFee
                                        ? `Drop this asset — fee ${money(row.dropFee)} (25% of remaining phase cost)`
                                        : "Drop this asset"
                                  }
                                  aria-label={
                                    row.dropped
                                      ? `Undo drop of ${row.name}`
                                      : `Drop ${row.name}`
                                  }
                                >
                                  <Trash2 className="size-4" />
                                </Button>
                              )}
                            </div>
                            {/* Fee callout while marked for drop — the cash
                                cost of abandoning this asset next step. */}
                            {row.dropped && (row.dropFee ?? 0) > 0 && (
                              <div className="mt-0.5 whitespace-nowrap text-[10px] font-bold text-destructive">
                                fee {money(row.dropFee ?? 0)}
                              </div>
                            )}
                          </div>
                        )}
                      </td>
                    )}
                    <td
                      className={cn(
                        TD,
                        "sticky z-10 font-bold",
                        STICKY_TINTS[variant][tintKey(row)],
                      )}
                      style={{ left: assetLeft }}
                    >
                      <span className="flex items-center gap-1.5">
                        {row.name}
                        {row.changed && (
                          <span
                            title={
                              row.changedKind === "both"
                                ? "Asset completed trial and changed status"
                                : row.changedKind === "status"
                                  ? "Asset status recently changed"
                                  : row.changedKind === "phase"
                                    ? "Asset completed trial and moved to next phase"
                                    : "Status or phase changed this year"
                            }
                            className="inline-block size-2 shrink-0 rounded-full bg-[#1ca8c0]"
                          />
                        )}
                        {row.infoAsset && (
                          <span className="text-muted-foreground/50 transition-colors hover:text-muted-foreground">
                            <AssetDetailDialog
                              asset={row.infoAsset}
                              emphasizeCashValue={emphasizeCashValue}
                              reinvestmentPercentage={reinvestmentPercentage}
                              ptrsReadingsEnabled={ptrsReadingsEnabled}
                            />
                          </span>
                        )}
                      </span>
                    </td>
                    {showHintColumn && (
                      <td className={td}>
                        {(() => {
                          const display = hintDisplay(row);
                          return display ? (
                            <div
                              className={cn(
                                "flex items-center justify-center",
                                display.className,
                              )}
                            >
                              {display.component}
                            </div>
                          ) : null;
                        })()}
                      </td>
                    )}
                    <td className={cn(td, "text-muted-foreground")}>
                      {row.ta}
                    </td>
                    <td className={cn(td, "text-muted-foreground")}>
                      {row.indication}
                    </td>
                    {isMarket ? (
                      // Classic On Market columns.
                      <>
                        <td className={tdNum}>
                          {money(
                            (row.revenueThisStep ?? 0) * reinvestmentPercentage,
                          )}
                        </td>
                        <td
                          className={cn(
                            tdNum,
                            valueOf(row) < 0 && "text-destructive",
                          )}
                        >
                          {money(valueOf(row))}
                        </td>
                        <td className={tdNum}>{money(row.pys)}</td>
                        <td className={tdNum}>{row.timeToPys ?? 0}</td>
                        <td className={tdNum}>{row.timeOnMarket ?? 0}</td>
                        <td className={tdNum}>{row.timeToExpiry}</td>
                      </>
                    ) : (
                      <>
                        <td className={td}>
                          <span className="inline-flex whitespace-nowrap rounded-full bg-secondary px-2.5 py-0.5 text-xs font-bold text-muted-foreground">
                            {row.phase}
                          </span>
                        </td>
                        <td className={tdNum}>{money(row.costThisYear)}</td>
                        <td className={tdNum}>
                          {distributionalPtrsEnabled ? (
                            // Classic distributional display: expected value
                            // + p10–p90 range + color-coded confidence.
                            <div className="whitespace-nowrap">
                              <span className="font-bold">
                                {row.ptrs.toFixed(1)}
                              </span>
                              {row.ptrsRangeLow !== undefined &&
                                row.ptrsRangeHigh !== undefined && (
                                  <div className="text-xs text-muted-foreground">
                                    p10–p90:{" "}
                                    {(row.ptrsRangeLow * 100).toFixed(0)}–
                                    {(row.ptrsRangeHigh * 100).toFixed(0)}%
                                  </div>
                                )}
                              {row.ptrsConfidence !== undefined && (
                                <div
                                  className={cn(
                                    "text-xs font-bold",
                                    row.ptrsConfidence >= 0.5
                                      ? "text-[#2f7d3f]"
                                      : row.ptrsConfidence >= 0.2
                                        ? "text-[#8a6d00]"
                                        : "text-destructive",
                                  )}
                                >
                                  conf {(row.ptrsConfidence * 100).toFixed(0)}%
                                </div>
                              )}
                            </div>
                          ) : ptrsReadingsEnabled ? (
                            <>
                              <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
                                <span className="font-bold">
                                  {row.ptrs.toFixed(1)}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  eff {row.ptrsEff.toFixed(1)}
                                </span>
                              </div>
                              <div className="mt-1 flex justify-end">
                                {interactive &&
                                !readOnly &&
                                onReadingsChange ? (
                                  <Select
                                    value={String(row.readings)}
                                    onValueChange={(value) =>
                                      onReadingsChange?.(row.id, Number(value))
                                    }
                                  >
                                    <SelectTrigger className="h-6 w-auto gap-1 whitespace-nowrap border-none bg-secondary/60 px-2 text-xs shadow-none">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="0">
                                        0 readings
                                        {row.readingsFree ? " · free" : ""}
                                      </SelectItem>
                                      {(row.readingCosts ?? []).map(
                                        (cost, i) => (
                                          <SelectItem
                                            key={i}
                                            value={String(i + 1)}
                                            // Classic: never block stepping
                                            // down; gate growth on cash.
                                            disabled={
                                              i + 1 > row.readings &&
                                              row.readingAffordableUpTo !==
                                                undefined &&
                                              i + 1 > row.readingAffordableUpTo
                                            }
                                          >
                                            {i + 1} reading{i > 0 ? "s" : ""} ·{" "}
                                            {money(cost)}
                                          </SelectItem>
                                        ),
                                      )}
                                    </SelectContent>
                                  </Select>
                                ) : readOnly &&
                                  row.readings === 0 ? null : readOnly ? (
                                  <span className="text-xs text-muted-foreground">
                                    {row.readings} readings
                                  </span>
                                ) : null}
                              </div>
                            </>
                          ) : (
                            <span className="font-bold">
                              {row.ptrs.toFixed(1)}
                            </span>
                          )}
                        </td>
                        {interimObservationsEnabled && (
                          <td className={td}>
                            {row.interim === "positive" ? (
                              <span className="flex items-center gap-1 text-xs font-bold text-[#2f7d3f]">
                                <CircleCheck className="size-3.5" />
                                Positive
                              </span>
                            ) : row.interim === "negative" ? (
                              <span className="flex items-center gap-1 text-xs font-bold text-[#8a6d00]">
                                <TriangleAlert className="size-3.5" />
                                Negative
                              </span>
                            ) : row.interim === "pending" ? (
                              <span className="text-xs text-muted-foreground">
                                Pending
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground/40">
                                –
                              </span>
                            )}
                          </td>
                        )}
                        <td className={tdNum}>
                          {money(row.remainingPhaseCost)}
                        </td>
                        <td className={tdNum}>{row.remainingPhaseTime}</td>
                        <td
                          className={cn(
                            tdNum,
                            valueOf(row) < 0 && "text-destructive",
                          )}
                        >
                          {money(valueOf(row))}
                        </td>
                        <td className={tdNum}>x{row.eroi.toFixed(1)}</td>
                        <td className={tdNum}>{money(row.pys)}</td>
                        <td className={tdNum}>{row.timeToExpiry}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* scroll hints */}
          <div
            aria-hidden
            className={cn(
              "pointer-events-none absolute inset-y-0 right-0 z-30 w-12 bg-gradient-to-l from-card to-transparent transition-opacity duration-200",
              fade.right ? "opacity-100" : "opacity-0",
            )}
          />
          <div
            aria-hidden
            className={cn(
              "pointer-events-none absolute inset-x-0 bottom-0 z-30 h-10 bg-gradient-to-t from-card to-transparent transition-opacity duration-200",
              fade.bottom ? "opacity-100" : "opacity-0",
            )}
          />
        </div>
      )}
    </div>
  );
}
