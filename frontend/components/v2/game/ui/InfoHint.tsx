"use client";

import { Info } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

/**
 * Minimal info affordance: a quiet ⓘ that opens a titled note on click
 * (popover, not hover). Feed it entries from lib/information-dictionary-game.
 */
export function InfoHint({
  title,
  description,
  side,
  className,
}: {
  title: string;
  description: string;
  /** Which side the note opens on (e.g. "left" near the screen edge). */
  side?: "top" | "right" | "bottom" | "left";
  className?: string;
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`About ${title}`}
          className={cn(
            "inline-flex text-muted-foreground/40 transition-colors hover:text-muted-foreground data-[state=open]:text-primary",
            className,
          )}
        >
          <Info className="size-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent side={side} className="w-auto max-w-[300px] rounded p-3">
        <p className="text-xs font-bold">{title}</p>
        <p className="mt-1 whitespace-pre-line text-xs font-light leading-relaxed text-muted-foreground">
          {description}
        </p>
      </PopoverContent>
    </Popover>
  );
}
