"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/** One launcher on the right-hand rail; opens a game board side panel. */
export function RailButton({
  icon: Icon,
  label,
  onClick,
  active = false,
  badge,
}: {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  active?: boolean;
  /** Small count bubble, e.g. assets available in the BD market. */
  badge?: number;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onClick}
          aria-label={label}
          className={cn(
            "relative flex size-12 items-center justify-center rounded transition-colors",
            active
              ? "bg-[var(--accent-soft)] text-primary"
              : "bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground",
          )}
        >
          <Icon className="size-5" />
          {badge !== undefined && badge > 0 && (
            <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-card px-1 text-[10px] font-bold text-primary">
              {badge}
            </span>
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent side="left">{label}</TooltipContent>
    </Tooltip>
  );
}
