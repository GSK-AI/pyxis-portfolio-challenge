"use client";

import type { ReactNode } from "react";
import { PanelRightClose } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { InfoHint } from "./InfoHint";
import { FadeScroll } from "./FadeScroll";
import { DockPanel } from "./DockPanel";

import type { LucideIcon } from "lucide-react";

export interface BoardSection {
  key: string;
  title: string;
  /** Rail launcher icon for this board. */
  icon: LucideIcon;
  /** Small count next to the title, e.g. BD assets available. */
  badge?: number;
  /** Explanatory note behind the title's info icon. */
  info?: { title: string; description: string };
  /**
   * Skip the 400px inner scroll cap and let the panel body scroll instead.
   * For tall content (stacked charts) where an inner scroller would hide
   * the lower items behind a fold nobody notices.
   */
  fullHeight?: boolean;
  content: ReactNode;
}

/**
 * Boards panel: slides in from the right — docked (pushing the dashboard
 * left) at 2xl+, overlaid below that, see DockPanel. All boards live here
 * as collapsible sections; the panel body scrolls.
 */
export function BoardsPanel({
  open,
  onClose,
  sections,
  activeSection,
  onActiveSectionChange,
}: {
  open: boolean;
  onClose: () => void;
  sections: BoardSection[];
  activeSection: string;
  onActiveSectionChange: (key: string) => void;
}) {
  return (
    <DockPanel open={open} onClose={onClose}>
      <header className="flex items-center gap-2 border-b border-foreground/5 px-4 py-3">
        <h2 className="text-sm font-bold tracking-wide">Boards</h2>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto size-8"
              onClick={onClose}
              aria-label="Close boards panel"
            >
              <PanelRightClose className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">Close panel</TooltipContent>
        </Tooltip>
      </header>

      <div className="v2-scroll flex-1 overflow-y-auto px-4 py-2">
        <Accordion
          type="single"
          collapsible
          value={activeSection}
          onValueChange={(value) => value && onActiveSectionChange(value)}
        >
          {sections.map((section) => (
            <AccordionItem
              key={section.key}
              value={section.key}
              className="mb-1 border-none"
            >
              <div className="relative">
                <AccordionTrigger className="rounded bg-secondary/40 px-3 py-3 text-sm font-bold tracking-wide transition-colors hover:bg-gradient-to-r hover:from-[#eef4fc] hover:to-[#f3f4f6] hover:no-underline data-[state=open]:bg-gradient-to-r data-[state=open]:from-[#eef4fc] data-[state=open]:to-[#f3f4f6]">
                  <span className="flex items-center gap-2">
                    {section.title}
                    {section.badge !== undefined && section.badge > 0 && (
                      <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-xs font-bold text-primary">
                        {section.badge}
                      </span>
                    )}
                  </span>
                </AccordionTrigger>
                {/* Outside the trigger (no nested buttons); sits by the chevron,
                    anchored to the title row only. */}
                {section.info && (
                  <span className="absolute inset-y-0 right-9 flex items-center">
                    <InfoHint {...section.info} side="left" />
                  </span>
                )}
              </div>
              <AccordionContent className="px-3 pb-5 pt-4">
                {section.fullHeight ? (
                  section.content
                ) : (
                  <FadeScroll className="max-h-[400px]">
                    {section.content}
                  </FadeScroll>
                )}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </DockPanel>
  );
}
