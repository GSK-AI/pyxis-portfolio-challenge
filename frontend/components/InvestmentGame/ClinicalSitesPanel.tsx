"use client";

import { formatDisplayNumber } from "@/lib/numbers";
import { InformationButton } from "@/components/InformationButton";
import { AlertTriangle, Plus } from "lucide-react";
import SiteCubes from "./SiteCubes";

export const CLINICAL_SITES_INFO = `Clinical sites are the physical capacity that runs your trials. Each operational site hosts one In-Development asset at a time, so your number of sites is a hard cap on how many trials you can run concurrently.

Managing sites:
- Occupied sites (solid) are currently running a trial.
- Free sites (outline) are ready to take on a new asset next year.
- Sites under construction (dashed) show the years remaining until they come online.

Buying a site:
- "Buy site" purchases one new site on a Fibonacci price curve — each site costs more than the last.
- A purchased site takes a couple of years to build before it becomes operational.

Site auction (PvP):
- Periodically an extra site is put up for a sealed-bid auction against your opponents.
- The highest bidder wins the site and pays their bid; bid within your cash.`;

export default function ClinicalSitesPanel({
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
  // How many free cubes light up as "incoming" (an asset you toggled this turn
  // will fill them next year). Asset-index allocation caps this at free_sites.
  const incoming = Math.min(Math.max(pendingIncoming, 0), freeSites);
  // Selected more new trials than there are free sites: the environment grants
  // sites in asset order and turns the rest into costless no-ops (they stay
  // idle). Warn the player so the highlight/table mismatch is expected.
  const overflow = Math.max(0, pendingIncoming - freeSites);

  const canAfford = nextSitePurchaseCost <= playerCash;
  const overCash = siteBid > playerCash;
  const bidCap = Math.min(maxSiteBid, playerCash);

  return (
    <div className="flex flex-col rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-gray-700">Clinical Sites</h3>
        <InformationButton
          title="Clinical Sites — Trial Capacity"
          description={CLINICAL_SITES_INFO}
        />
      </div>

      {/* Summary counts */}
      <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-600">
        <span>
          Operational:{" "}
          <span className="font-semibold text-gray-800">
            {operationalSites}
          </span>
        </span>
        <span>
          Occupied:{" "}
          <span className="font-semibold text-teal-600">{sitesOccupied}</span>
        </span>
        <span>
          Free: <span className="font-semibold text-gray-800">{freeSites}</span>
        </span>
        {sitesInDevelopment.length > 0 && (
          <span>
            Building:{" "}
            <span className="font-semibold text-amber-600">
              {sitesInDevelopment.length}
            </span>
          </span>
        )}
      </div>

      {/* Cubes */}
      <SiteCubes
        sitesOccupied={sitesOccupied}
        freeSites={freeSites}
        sitesInDevelopment={sitesInDevelopment}
        incoming={incoming}
        size="md"
      />

      {incoming > 0 && (
        <p className="mt-2 text-[10px] text-teal-600">
          {incoming} selected asset{incoming === 1 ? "" : "s"} will start in the
          highlighted site{incoming === 1 ? "" : "s"} next year.
        </p>
      )}

      {overflow > 0 && (
        <div className="mt-2 flex items-start gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-2 py-1.5 text-[10px] text-amber-700">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          <span>
            Not enough free sites: {overflow} selected asset
            {overflow === 1 ? "" : "s"} won&apos;t start this year. Sites go to
            the assets nearest the top of the table; those lower down stay idle
            at no cost.
          </span>
        </div>
      )}

      {/* Buy-site action */}
      <div className="mt-3 border-t border-gray-100 pt-3">
        <button
          type="button"
          disabled={!canAfford && !buySite}
          onClick={() => onBuySiteChange(!buySite)}
          className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-xs font-medium transition-colors ${
            buySite
              ? "border-teal-500 bg-teal-500 text-white"
              : canAfford
                ? "border-gray-200 bg-gray-50 text-gray-700 hover:border-teal-300 hover:bg-teal-50"
                : "border-gray-150 cursor-not-allowed bg-gray-50 text-gray-300"
          }`}
        >
          <span className="flex items-center gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            {buySite ? "Buying a site" : "Buy site"}
          </span>
          <span className={buySite ? "text-white" : "text-gray-500"}>
            {formatDisplayNumber(nextSitePurchaseCost)}
          </span>
        </button>
        {!canAfford && !buySite && (
          <p className="mt-1 text-[10px] font-medium text-red-500">
            Not enough cash for a new site.
          </p>
        )}
        {buySite && (
          <p className="mt-1 text-[10px] text-gray-500">
            Build takes a couple of years before the site comes online.
          </p>
        )}
      </div>

      {/* Site auction (only on auction years) */}
      {siteAuctionActive && (
        <div className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-2.5">
          <div className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold text-blue-700">
            Site auction this year
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500">Bid (£):</span>
            <input
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
              className={`w-32 rounded border px-2 py-1 text-[11px] ${
                overCash
                  ? "border-red-300 bg-red-50 text-red-700"
                  : "border-gray-200 bg-white text-gray-700"
              }`}
            />
            {siteBid > 0 && (
              <span className="text-[10px] text-gray-500">
                {formatDisplayNumber(siteBid)}
              </span>
            )}
            {overCash && (
              <span className="text-[10px] font-medium text-red-600">
                exceeds cash
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
