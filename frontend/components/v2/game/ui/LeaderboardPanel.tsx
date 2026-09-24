"use client";

import { PanelRightClose, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { EmptyState } from "./EmptyState";
import { CompetitorCard, type CompetitorInfo } from "./Competitors";
import { FadeScroll } from "./FadeScroll";
import { DockPanel } from "./DockPanel";

/**
 * Dedicated leaderboard panel: the current game's standings — you and
 * every competitor as ranked cards (same data as the top grid, in full).
 * Docked at 2xl+, overlaid below that; see DockPanel.
 */
export function LeaderboardPanel({
  open,
  onClose,
  standings,
}: {
  open: boolean;
  onClose: () => void;
  standings: CompetitorInfo[];
}) {
  return (
    <DockPanel open={open} onClose={onClose}>
      <header className="flex items-center gap-2 border-b border-foreground/5 px-4 py-3">
        <h2 className="text-sm font-bold tracking-wide">Leaderboard</h2>
        <span className="text-xs text-muted-foreground/70">
          ranked by net cash flow
        </span>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto size-8"
              onClick={onClose}
              aria-label="Close leaderboard"
            >
              <PanelRightClose className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">Close panel</TooltipContent>
        </Tooltip>
      </header>

      <FadeScroll className="h-full px-4 py-3">
        {standings.length === 0 ? (
          <EmptyState
            icon={Trophy}
            message="No standings yet"
            hint="Standings appear in multiplayer games"
          />
        ) : (
          <div className="space-y-2">
            {standings.map((standing) => (
              <CompetitorCard key={standing.name} {...standing} />
            ))}
          </div>
        )}
      </FadeScroll>
    </DockPanel>
  );
}
