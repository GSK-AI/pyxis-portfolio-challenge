"use client";

import { Radar } from "lucide-react";
import type { AlertType } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/numbers";
import { EmptyState } from "./EmptyState";

/**
 * Competitive Intelligence board (v2 skin, classic AlertsPanel logic):
 * the feed of opponent activity your network uncovered, newest first.
 */

const ALERT_STYLES: Record<
  string,
  { label: string; card: string; text: string }
> = {
  drug_release: {
    label: "DRUG RELEASE",
    card: "bg-gradient-to-r from-[#e0f3e6] to-[#f2faf4]",
    text: "text-[#2f7d3f]",
  },
  bd_deal: {
    label: "BD DEAL",
    card: "bg-gradient-to-r from-[#e2edfb] to-[#f4f8fd]",
    text: "text-primary",
  },
  pipeline_leak: {
    label: "PIPELINE LEAK",
    card: "bg-gradient-to-r from-[#fff3cd] to-[#fffaf0]",
    text: "text-[#8a6d00]",
  },
  clinical_site_deal: {
    label: "CLINICAL SITE",
    card: "bg-gradient-to-r from-[#efe7fb] to-[#f9f6fd]",
    text: "text-[#6d28d9]",
  },
  be_spend: {
    label: "BRAND PUSH",
    card: "bg-gradient-to-r from-[#fbe7ee] to-[#fdf5f8]",
    text: "text-[#be185d]",
  },
  dc_spend: {
    label: "DEMAND PUSH",
    card: "bg-gradient-to-r from-[#dff4f8] to-[#f0fafc]",
    text: "text-[#15717d]",
  },
};

// --- identical message formatting to the classic AlertsPanel ---
function formatAlertMessage(alert: AlertType): string {
  const details = alert.details || {};
  const indication = alert.indication_name ? ` — ${alert.indication_name}` : "";
  switch (alert.event_type) {
    case "drug_release":
      return `${alert.agent_id} launched a drug in ${alert.therapeutic_area}${indication}${details.asset_name ? ` (${details.asset_name})` : ""}`;
    case "bd_deal":
      return `${alert.agent_id} acquired ${details.asset_name || "an asset"} in ${alert.therapeutic_area}${indication}`;
    case "pipeline_leak":
      return `${alert.agent_id} has a drug in ${details.new_phase || "development"} (${alert.therapeutic_area}${indication})`;
    case "clinical_site_deal":
      return `${alert.agent_id} won a clinical site at auction for ${formatCurrency(details.price as number | null | undefined)}`;
    case "be_spend": {
      const count = (details.be_count as number | undefined) ?? 0;
      return `${alert.agent_id} boosted brand equity on ${count} drug${count === 1 ? "" : "s"} in ${alert.therapeutic_area}${indication}`;
    }
    case "dc_spend":
      return `${alert.agent_id} grew market demand in ${alert.therapeutic_area}${indication}`;
    default:
      return `${alert.agent_id} - ${alert.therapeutic_area}${indication}`;
  }
}
// --- end identical logic ---

export function IntelligenceBoard({
  alerts,
  playerAgentName,
}: {
  alerts: AlertType[];
  playerAgentName: string;
}) {
  // Classic: hide the player's own alerts, newest first.
  const relevantAlerts = alerts
    .filter((a) => a.agent_id !== playerAgentName)
    .sort((a, b) => b.step - a.step);

  if (relevantAlerts.length === 0) {
    return (
      <EmptyState
        icon={Radar}
        message="No intelligence reports yet"
        hint="Your network reports what it uncovers each year"
      />
    );
  }

  return (
    <div className="space-y-2">
      {relevantAlerts.map((alert, i) => {
        const style = ALERT_STYLES[alert.event_type] ?? {
          label: alert.event_type.toUpperCase(),
          card: "bg-secondary/40",
          text: "text-muted-foreground",
        };
        return (
          <div
            key={`${alert.step}-${alert.event_type}-${alert.agent_id}-${i}`}
            className={cn("space-y-1 rounded px-3 py-2.5", style.card)}
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "text-[10px] font-bold uppercase tracking-wider",
                  style.text,
                )}
              >
                {style.label}
              </span>
              <span className="text-[10px] text-muted-foreground">
                Year {alert.step}
              </span>
            </div>
            <p className="text-xs leading-relaxed">
              {formatAlertMessage(alert)}
            </p>
          </div>
        );
      })}
    </div>
  );
}
