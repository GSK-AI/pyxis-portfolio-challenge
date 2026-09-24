"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import type { ViewMode } from "@/components/InvestmentGame/Replay/useReplayState";

/**
 * Replay control row, aligned with the game's GameTopBar: identity +
 * meta on the left, State/Actions toggle, step navigation in the middle,
 * Exit on the right. Gradient at rest, glass when stuck.
 */
export function ReplayTopBar({
  numAgents,
  seed,
  viewMode,
  onViewModeChange,
  stepIndex,
  totalSteps,
  onStepChange,
  onPrev,
  onNext,
  onExit,
}: {
  numAgents: number;
  seed: number | null;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  stepIndex: number;
  totalSteps: number;
  onStepChange: (index: number) => void;
  onPrev: () => void;
  onNext: () => void;
  onExit: () => void;
}) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [stuck, setStuck] = useState(false);

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

  const lastStep = totalSteps - 1;

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
                ? "rounded-none border-b border-foreground/5 bg-card/80 backdrop-blur-md"
                : "rounded bg-gradient-to-r from-[#eef4fc] to-[#f3f4f6]",
            )}
          >
            <div className="mx-auto flex w-full max-w-[1560px] items-center gap-4">
              {/* Identity + meta */}
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

              <div className="flex shrink-0 items-center gap-2.5">
                <span className="text-sm font-bold tracking-wide">Replay</span>
                <span className="hidden whitespace-nowrap rounded-full bg-card px-2.5 py-0.5 text-xs text-muted-foreground lg:block">
                  {numAgents} agent{numAgents === 1 ? "" : "s"}
                  {seed !== null && ` · seed ${seed}`}
                </span>
              </div>

              <div className="h-[22px] w-px shrink-0 bg-input" />

              {/* State / Actions view toggle */}
              <div className="inline-flex shrink-0 items-center gap-1 rounded bg-secondary/60 p-1">
                {(["state", "action"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => onViewModeChange(mode)}
                    className={cn(
                      "rounded px-3 py-1 text-sm capitalize transition-colors",
                      viewMode === mode
                        ? "bg-card font-bold text-primary shadow-sm"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {mode === "state" ? "State" : "Actions"}
                  </button>
                ))}
              </div>

              {/* Step navigation */}
              <div className="flex min-w-0 flex-1 items-center justify-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onPrev}
                  disabled={stepIndex <= 0}
                  aria-label="Previous step"
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <span className="text-sm text-muted-foreground">Step</span>
                <Input
                  type="number"
                  min={0}
                  max={lastStep}
                  value={stepIndex}
                  onFocus={(e) => e.target.select()}
                  onChange={(e) => {
                    const raw = Number(e.target.value);
                    if (Number.isFinite(raw)) onStepChange(raw);
                  }}
                  className="h-8 w-16 bg-card text-center text-sm tabular-nums"
                />
                <span className="whitespace-nowrap text-sm tabular-nums text-muted-foreground">
                  / {lastStep}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onNext}
                  disabled={stepIndex >= lastStep}
                  aria-label="Next step"
                >
                  <ChevronRight className="size-4" />
                </Button>
                <Progress
                  value={lastStep > 0 ? (stepIndex / lastStep) * 100 : 0}
                  className="hidden h-1.5 max-w-[200px] xl:block"
                />
              </div>

              {/* Exit */}
              <Button
                variant="ghost"
                size="sm"
                onClick={onExit}
                className="shrink-0"
              >
                <X className="size-4" />
                Exit
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
