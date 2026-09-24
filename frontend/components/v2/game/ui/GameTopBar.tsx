"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Ban,
  CircleHelp,
  Focus,
  House,
  Loader2,
  Minimize2,
  Trophy,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ConfirmDialog } from "./ConfirmDialog";
import { RankBadge } from "./Competitors";
import { formatDisplayNumber } from "@/lib/numbers";

/**
 * Single control row for the game screen: home/identity on the left,
 * year progress in the middle, game controls on the right.
 *
 * At rest: subtle grey gradient, no border, no radius. Once it sticks
 * on scroll it switches to a glass treatment (blurred card + hairline).
 * Stuck state is detected with a sentinel just above the bar, so it
 * works in any scroll container.
 */
export function GameTopBar({
  year,
  totalYears,
  onRestart,
  onTour,
  onNextYear,
  onHome,
  advancing = false,
  agentsDeciding = false,
  bankrupt = false,
  focusView = false,
  onFocusViewChange,
  rank,
  netCashFlow,
  gameEnded = false,
  onViewResults,
}: {
  year: number;
  totalYears: number;
  onRestart: () => void;
  onTour?: () => void;
  onNextYear: () => void;
  /** In-game "home" is a state reset, not a navigation — pass to override the / link. */
  onHome?: () => void;
  advancing?: boolean;
  /** Opponents still "thinking" — Next Year waits (classic gating). */
  agentsDeciding?: boolean;
  /** Player is bankrupt: Next Year becomes a disabled "Bankrupt" state. */
  bankrupt?: boolean;
  /** Focus view: compact dashboard row, table first. Toggle sits with Home/Tour. */
  focusView?: boolean;
  onFocusViewChange?: (focusView: boolean) => void;
  /** Scoreboard: player rank and net cash flow, shown compactly on wide screens. */
  rank?: number;
  netCashFlow?: number;
  gameEnded?: boolean;
  onViewResults?: () => void;
}) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [stuck, setStuck] = useState(false);
  const [confirming, setConfirming] = useState<"home" | "restart" | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      ([entry]) => setStuck(!entry.isIntersecting),
      { threshold: 0 },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <div ref={sentinelRef} aria-hidden className="h-px" />
      <div
        className={cn(
          "sticky top-0 z-40 transition-all duration-200",
          stuck ? "p-0" : "pt-3",
        )}
      >
        <div
          className={cn(
            "transition-all duration-200",
            !stuck && "mx-auto w-full max-w-[1560px] px-4",
          )}
        >
          <div
            className={cn(
              "flex h-14 items-center gap-4 px-4 transition-all duration-200",
              stuck
                ? "rounded-none border-b border-foreground/5 backdrop-blur-md"
                : "rounded bg-gradient-to-r",
              // Focus view deepens the bar a step, so the mode reads at a
              // glance even after the dashboard below has collapsed.
              stuck
                ? focusView
                  ? "bg-secondary/85"
                  : "bg-card/80"
                : focusView
                  ? "from-[#dfe9f7] to-[#e6e8eb]"
                  : "from-[#eef4fc] to-[#f3f4f6]",
            )}
          >
            <div className="mx-auto flex w-full max-w-[1560px] items-center gap-4">
              {/* Identity */}
              <div className="flex shrink-0 items-center gap-2.5">
                <Image
                  src="/images/pyxis-app-icon-2.svg"
                  alt="Pyxis"
                  width={26}
                  height={26}
                />
                <span className="hidden text-sm font-bold tracking-wide xl:block">
                  Pyxis Portfolio Challenge
                </span>
              </div>

              <div className="h-[22px] w-px shrink-0 bg-input" />

              {/* Home + help, tight cluster */}
              <div className="flex shrink-0 items-center gap-0.5">
                <Tooltip>
                  <TooltipTrigger asChild>
                    {onHome ? (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setConfirming("home")}
                        aria-label="Home"
                      >
                        <House className="size-4" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        asChild
                        aria-label="Home"
                      >
                        <Link href="/">
                          <House className="size-4" />
                        </Link>
                      </Button>
                    )}
                  </TooltipTrigger>
                  <TooltipContent>Home</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={onTour}
                      disabled={!onTour}
                      aria-label="Tour"
                    >
                      <CircleHelp className="size-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {onTour ? "Tour" : "Tour — coming to the new experience"}
                  </TooltipContent>
                </Tooltip>

                {/* Focus view: collapses the dashboard into one row so the
                    asset table gets the height. Labelled (no tooltip — the
                    text says it); active state gets a filled pill. */}
                {onFocusViewChange && (
                  <Button
                    id="v2-tour-focus"
                    variant="ghost"
                    size="sm"
                    onClick={() => onFocusViewChange(!focusView)}
                    aria-pressed={focusView}
                    className={cn(
                      "ml-1 gap-1.5 rounded-full px-3 text-xs font-normal",
                      focusView
                        ? "bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary"
                        : "text-muted-foreground",
                    )}
                  >
                    {focusView ? (
                      <Minimize2 className="size-3.5" />
                    ) : (
                      <Focus className="size-3.5" />
                    )}
                    {focusView ? "Exit focus view" : "Focus view"}
                  </Button>
                )}
              </div>

              {/* Year progress */}
              <div className="flex min-w-0 flex-1 items-center justify-center gap-3">
                <span className="min-w-[120px] shrink-0 text-right text-sm tabular-nums text-muted-foreground">
                  Year{" "}
                  <span className="font-bold text-foreground">
                    {Math.min(year, totalYears)}
                  </span>{" "}
                  of {totalYears}
                </span>
                <Progress
                  value={Math.min((year / totalYears) * 100, 100)}
                  className="h-1.5 max-w-[280px]"
                />
              </div>

              {/* Scoreboard: rank + net cash flow */}
              {(rank !== undefined || netCashFlow !== undefined) && (
                <div className="hidden shrink-0 items-center gap-2 text-sm lg:flex">
                  {rank !== undefined && (
                    <>
                      <span className="text-muted-foreground">Your rank</span>
                      <RankBadge rank={rank} />
                    </>
                  )}
                  {netCashFlow !== undefined && (
                    <>
                      <span className="text-muted-foreground/30">·</span>
                      <span className="text-muted-foreground">
                        Net Cash Flow
                      </span>
                      <span
                        className={cn(
                          "font-bold tabular-nums",
                          netCashFlow < 0 ? "text-destructive" : undefined,
                        )}
                      >
                        {formatDisplayNumber(netCashFlow)}
                      </span>
                    </>
                  )}
                  <div className="h-[22px] w-px bg-input" />
                </div>
              )}

              {/* Controls */}
              <div className="flex shrink-0 items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirming("restart")}
                  className={cn(year <= 1 && "invisible")}
                >
                  Start Over
                </Button>
                {/* The tour anchor is this wrapper rather than the row above:
                    Start Over holds its space while invisible in year 1, so
                    anchoring the row would spotlight the gap where it sits. */}
                <div id="v2-tour-controls" className="flex items-center">
                  {gameEnded ? (
                    <Button
                      size="sm"
                      className="rounded shadow-[0_0_14px_rgba(62,113,210,0.45)] transition-shadow hover:shadow-[0_0_22px_rgba(62,113,210,0.65)]"
                      onClick={onViewResults}
                    >
                      View Results
                      <Trophy className="size-4" />
                    </Button>
                  ) : bankrupt ? (
                    // Bankrupt: the game auto-advances on its own — show a
                    // disabled state in place of the action.
                    <Button
                      size="sm"
                      variant="secondary"
                      className="rounded"
                      disabled
                      title="You are bankrupt — the remaining years advance automatically"
                    >
                      Bankrupt
                      <Ban className="size-4" />
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      className="rounded shadow-[0_0_14px_rgba(62,113,210,0.45)] transition-shadow hover:shadow-[0_0_22px_rgba(62,113,210,0.65)]"
                      onClick={onNextYear}
                      disabled={advancing || agentsDeciding}
                      title={agentsDeciding ? "Agents deciding…" : undefined}
                    >
                      Next Year
                      {advancing || agentsDeciding ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <ArrowRight className="size-4" />
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirming === "home"}
        onOpenChange={(open) => !open && setConfirming(null)}
        title="Leave the game?"
        description={`You are in year ${year} of ${totalYears}. Leaving ends this game — your progress will be lost and you'll return to the start screen.`}
        confirmLabel="Leave Game"
        destructive
        onConfirm={() => onHome?.()}
      />
      <ConfirmDialog
        open={confirming === "restart"}
        onOpenChange={(open) => !open && setConfirming(null)}
        title="Start over?"
        description={`This ends the current game in year ${year} and starts a fresh one from year 1. This can't be undone.`}
        confirmLabel="Start Over"
        destructive
        onConfirm={onRestart}
      />
    </>
  );
}
