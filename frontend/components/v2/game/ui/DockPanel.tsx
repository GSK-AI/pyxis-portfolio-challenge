"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Shell for the right-hand side panels (boards, leaderboard).
 *
 * At 2xl+ it docks: a flex item whose width animates between 0 and 440px,
 * pushing the dashboard left. Below that the dashboard has no width to
 * spare — 440px of push leaves the table squeezed — so the panel slides
 * over it instead, frosted and lifted by a shadow. Requires a `relative
 * overflow-hidden` parent (the closed panel parks off-canvas to the right).
 *
 * In overlay mode a scrim sits behind it so clicking the dashboard closes
 * the panel — the overlay covers the top bar's right edge, so that and the
 * panel's own close button are the ways out. Docked, there is no scrim: the
 * dashboard stays fully interactive beside the panel.
 */
export function DockPanel({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close panel"
          onClick={onClose}
          className="absolute inset-0 z-40 cursor-default bg-foreground/5 2xl:hidden"
        />
      )}
      <aside
        className={cn(
          "absolute inset-y-0 right-0 z-50 w-[440px] shadow-[-8px_0_32px_rgba(0,0,0,0.12)] transition-transform duration-300",
          open ? "translate-x-0" : "translate-x-full",
          "2xl:relative 2xl:z-auto 2xl:h-full 2xl:shrink-0 2xl:translate-x-0 2xl:overflow-hidden 2xl:shadow-none 2xl:transition-[width]",
          open ? "2xl:w-[440px]" : "2xl:w-0",
        )}
      >
        <div className="flex h-full w-[440px] flex-col border-l border-foreground/5 bg-card/95 backdrop-blur-md 2xl:bg-card 2xl:backdrop-blur-none">
          {children}
        </div>
      </aside>
    </>
  );
}
