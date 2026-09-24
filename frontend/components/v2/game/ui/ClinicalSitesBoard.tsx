"use client";

import { Plus, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { formatDisplayNumber } from "@/lib/numbers";
import SiteCubes from "@/components/InvestmentGame/SiteCubes";

/**
 * Clinical Sites board (v2 skin, classic logic): capacity counts, the
 * site cube grid, buy-site toggle on the Fibonacci curve, and the PvP
 * auction bid on auction years. Reuses the classic SiteCubes grid.
 */
export function ClinicalSitesBoard({
  operationalSites,
  sitesOccupied,
  freeSites,
  sitesInDevelopment,
  nextSitePurchaseCost,
  playerCash,
  buySite,
  onBuySiteChange,
  siteAuctionActive,
  siteBid,
  maxSiteBid,
  onSiteBidChange,
  pendingIncoming = 0,
}: {
  operationalSites: number;
  sitesOccupied: number;
  freeSites: number;
  sitesInDevelopment: number[];
  nextSitePurchaseCost: number;
  playerCash: number;
  buySite: boolean;
  onBuySiteChange: (buy: boolean) => void;
  siteAuctionActive: boolean;
  siteBid: number;
  maxSiteBid: number;
  onSiteBidChange: (bid: number) => void;
  pendingIncoming?: number;
}) {
  // --- identical logic to the classic ClinicalSitesPanel ---
  const incoming = Math.min(Math.max(pendingIncoming, 0), freeSites);
  const overflow = Math.max(0, pendingIncoming - freeSites);
  const canAfford = nextSitePurchaseCost <= playerCash;
  const overCash = siteBid > playerCash;
  const bidCap = Math.min(maxSiteBid, playerCash);
  // --- end identical logic ---

  return (
    <div className="space-y-4">
      {/* Summary counts */}
      <div className="grid grid-cols-4 gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
            Operational
          </div>
          <div className="text-sm font-bold tabular-nums">
            {operationalSites}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
            Occupied
          </div>
          <div className="text-sm font-bold tabular-nums text-[#15717d]">
            {sitesOccupied}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
            Free
          </div>
          <div className="text-sm font-bold tabular-nums">{freeSites}</div>
        </div>
        {sitesInDevelopment.length > 0 && (
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
              Building
            </div>
            <div className="text-sm font-bold tabular-nums text-[#b45309]">
              {sitesInDevelopment.length}
            </div>
          </div>
        )}
      </div>

      <SiteCubes
        sitesOccupied={sitesOccupied}
        freeSites={freeSites}
        sitesInDevelopment={sitesInDevelopment}
        incoming={incoming}
        size="sm"
      />

      {incoming > 0 && (
        <p className="text-xs text-[#15717d]">
          {incoming} selected asset{incoming === 1 ? "" : "s"} will start in the
          highlighted site{incoming === 1 ? "" : "s"} next year.
        </p>
      )}

      {overflow > 0 && (
        <div className="flex items-start gap-2 rounded bg-[#fff7e0] px-3 py-2 text-xs text-[#8a6d00]">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
          <span>
            Not enough free sites: {overflow} selected asset
            {overflow === 1 ? "" : "s"} won&apos;t start this year. Sites go to
            the assets nearest the top of the table; those lower down stay idle
            at no cost.
          </span>
        </div>
      )}

      {/* Buy-site action */}
      <div>
        <button
          type="button"
          disabled={!canAfford && !buySite}
          onClick={() => onBuySiteChange(!buySite)}
          className={cn(
            "flex w-full items-center justify-between rounded px-3 py-2.5 text-sm transition-colors",
            buySite
              ? "bg-primary font-bold text-primary-foreground"
              : canAfford
                ? "bg-card font-bold text-primary ring-1 ring-inset ring-primary/30 hover:bg-[var(--accent-soft)] hover:ring-primary/50"
                : "cursor-not-allowed bg-secondary/30 text-muted-foreground/40",
          )}
        >
          <span className="flex items-center gap-1.5">
            <Plus className="size-4" />
            {buySite ? "Buying a site" : "Buy site"}
          </span>
          <span
            className={cn(
              "tabular-nums",
              buySite ? "text-primary-foreground/80" : "text-muted-foreground",
            )}
          >
            {formatDisplayNumber(nextSitePurchaseCost)}
          </span>
        </button>
        {!canAfford && !buySite && (
          <p className="mt-1.5 text-xs text-destructive">
            Not enough cash for a new site.
          </p>
        )}
        {buySite && (
          <p className="mt-1.5 text-xs text-muted-foreground">
            Build takes a couple of years before the site comes online.
          </p>
        )}
      </div>

      {/* Site auction (only on auction years) */}
      {siteAuctionActive && (
        <div className="space-y-2 rounded bg-gradient-to-r from-[#eef4fc] to-white p-3">
          <div className="text-xs font-bold text-primary">
            Site auction this year
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Bid (£)</span>
            <Input
              type="number"
              min={0}
              max={bidCap}
              step={1_000_000}
              value={siteBid === 0 ? "" : siteBid}
              placeholder="0"
              onChange={(e) => {
                const raw = Number(e.target.value);
                const clamped = Number.isFinite(raw)
                  ? Math.max(0, Math.min(raw, bidCap))
                  : 0;
                onSiteBidChange(clamped);
              }}
              className={cn(
                "h-8 w-36 bg-card text-sm",
                overCash && "border-destructive text-destructive",
              )}
            />
            {siteBid > 0 && (
              <span className="text-xs tabular-nums text-muted-foreground">
                {formatDisplayNumber(siteBid)}
              </span>
            )}
            {overCash && (
              <span className="text-xs font-bold text-destructive">
                exceeds cash
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
