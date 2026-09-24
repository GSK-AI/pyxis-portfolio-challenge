"use client";

import type { AlertType } from "@/lib/definitionsGameZ";
import { InformationButton } from "@/components/InformationButton";
import { formatCurrency } from "@/lib/numbers";

export const ALERTS_INFO = `Competitive intelligence provides information about your opponents' activities. Not all actions are visible — you only learn what your intelligence network uncovers.

Alert Types:

DRUG RELEASE — A competitor has successfully launched a drug onto the market. This is always reported. Check the Sales Market panel to see how this affects your market share in that indication.

BD DEAL — A competitor acquired an asset from the BD market. This tells you which therapeutic area they're investing in and may signal future competition in that indication.

PIPELINE LEAK — Your intelligence network discovered that a competitor has a drug in development. This reveals their trial phase but not full details. Pipeline leaks are probabilistic — you won't see all competitor activity, and some years you may get no leaks at all.

CLINICAL SITE — A competitor won an extra clinical site at auction, along with the bid they paid. This signals they are expanding trial capacity and how much they are willing to spend to do so.

BRAND PUSH — Your intelligence caught a competitor spending on brand equity for one or more drugs in an indication. This signals they are defending or growing share there. Marketing leaks are probabilistic — you won't catch every spend.

DEMAND PUSH — A competitor spent on demand creation to grow the overall market for an indication. This lifts revenue for every drug in that indication, so expect the market there to expand.

Use this information to anticipate competition: if a competitor is developing in an indication you're targeting, they may beat you to first-mover exclusivity.`;

const ALERT_STYLES: Record<
  string,
  { label: string; bgColor: string; textColor: string; borderColor: string }
> = {
  drug_release: {
    label: "DRUG RELEASE",
    bgColor: "bg-green-50",
    textColor: "text-green-800",
    borderColor: "border-green-200",
  },
  bd_deal: {
    label: "BD DEAL",
    bgColor: "bg-blue-50",
    textColor: "text-blue-800",
    borderColor: "border-blue-200",
  },
  pipeline_leak: {
    label: "PIPELINE LEAK",
    bgColor: "bg-orange-50",
    textColor: "text-orange-800",
    borderColor: "border-orange-200",
  },
  clinical_site_deal: {
    label: "CLINICAL SITE",
    bgColor: "bg-purple-50",
    textColor: "text-purple-800",
    borderColor: "border-purple-200",
  },
  be_spend: {
    label: "BRAND PUSH",
    bgColor: "bg-rose-50",
    textColor: "text-rose-800",
    borderColor: "border-rose-200",
  },
  dc_spend: {
    label: "DEMAND PUSH",
    bgColor: "bg-cyan-50",
    textColor: "text-cyan-800",
    borderColor: "border-cyan-200",
  },
};

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

export default function AlertsPanel({
  alerts,
  playerAgentName,
}: {
  alerts: AlertType[];
  playerAgentName: string;
}) {
  // Filter out player's own alerts and sort most recent first
  const relevantAlerts = alerts
    .filter((a) => a.agent_id !== playerAgentName)
    .sort((a, b) => b.step - a.step);

  return (
    <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-gray-700">
          Competitive Intelligence
        </h3>
        <InformationButton
          title="Competitive Intelligence"
          description={ALERTS_INFO}
        />
      </div>
      {relevantAlerts.length === 0 ? (
        <p className="text-xs text-gray-400">No intelligence reports yet</p>
      ) : (
        <div className="flex-1 space-y-2 overflow-y-auto">
          {relevantAlerts.map((alert, i) => {
            const style = ALERT_STYLES[alert.event_type] || {
              label: alert.event_type.toUpperCase(),
              bgColor: "bg-gray-50",
              textColor: "text-gray-800",
              borderColor: "border-gray-200",
            };
            return (
              <div
                key={`${alert.step}-${alert.event_type}-${alert.agent_id}-${i}`}
                className={`rounded border ${style.borderColor} ${style.bgColor} px-3 py-2`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${style.textColor}`}
                  >
                    {style.label}
                  </span>
                  <span className="text-[10px] text-gray-500">
                    Year {alert.step}
                  </span>
                </div>
                <p className={`mt-1 text-xs ${style.textColor}`}>
                  {formatAlertMessage(alert)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
