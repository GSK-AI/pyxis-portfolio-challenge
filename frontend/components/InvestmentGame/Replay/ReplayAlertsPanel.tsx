"use client";

import type { AlertType } from "@/lib/definitionsGameZ";

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
};

function formatAlertMessage(
  alert: AlertType,
  agentDisplayNames: Record<string, string>,
): string {
  const details = alert.details || {};
  const indication = alert.indication_name ? ` — ${alert.indication_name}` : "";
  const name = agentDisplayNames[alert.agent_id] ?? alert.agent_id;
  switch (alert.event_type) {
    case "drug_release":
      return `${name} launched a drug in ${alert.therapeutic_area}${indication}${details.asset_name ? ` (${details.asset_name})` : ""}`;
    case "bd_deal":
      return `${name} acquired ${details.asset_name || "an asset"} in ${alert.therapeutic_area}${indication}`;
    case "pipeline_leak":
      return `${name} has a drug in ${details.new_phase || "development"} (${alert.therapeutic_area}${indication})`;
    default:
      return `${name} - ${alert.therapeutic_area}${indication}`;
  }
}

interface ReplayAlertsPanelProps {
  alerts: AlertType[];
  currentStep: number;
  agentDisplayNames: Record<string, string>;
}

export default function ReplayAlertsPanel({
  alerts,
  currentStep,
  agentDisplayNames,
}: ReplayAlertsPanelProps) {
  // Show all alerts up to and including current step, most recent first
  const relevantAlerts = alerts
    .filter((a) => a.step <= currentStep)
    .sort((a, b) => b.step - a.step);

  return (
    <div className="flex h-[460px] flex-col rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">
        Competitive Intelligence
      </h3>
      {relevantAlerts.length === 0 ? (
        <p className="text-xs text-gray-400">No intelligence reports yet</p>
      ) : (
        <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
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
                  {formatAlertMessage(alert, agentDisplayNames)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
