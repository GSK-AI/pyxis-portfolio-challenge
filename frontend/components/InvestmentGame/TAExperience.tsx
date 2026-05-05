"use client";

import { InformationButton } from "../InformationButton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface TAExperienceProps {
  taExperience: Record<string, number>;
  maxExperience?: number; // Experience needed for full knowledge in one TA (from config)
  maxTotalExperience?: number | null; // Hard cap on total experience across all TAs
}

// TA display names and colors
const TA_CONFIG: Record<string, { label: string; color: string }> = {
  oncology: {
    label: "Oncology",
    color: "bg-purple-500",
  },
  "respiratory and immunology": {
    label: "Resp & Immuno",
    color: "bg-blue-500",
  },
  "vaccines and infectious disease": {
    label: "Vaccines & ID",
    color: "bg-green-500",
  },
};

export default function TAExperience({
  taExperience,
  maxExperience = 30,
  maxTotalExperience,
}: TAExperienceProps) {
  if (!taExperience || Object.keys(taExperience).length === 0) {
    return null;
  }

  const totalExperience = Object.values(taExperience).reduce(
    (sum, exp) => sum + exp,
    0,
  );

  return (
    <div className="w-full rounded-lg bg-gray-50 p-2">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs font-medium text-gray-600">TA Experience</span>
        <InformationButton
          title="Therapeutic Area Experience"
          description="Your experience in each therapeutic area affects how accurately you can estimate PTRS. Higher experience means less uncertainty. Experience is gained by completing trials."
          buttonClassName="w-3 h-3"
        />
      </div>

      {/* Total / Max display */}
      {maxTotalExperience && (
        <div className="mb-2 text-center">
          <span className="text-sm font-medium text-gray-700">
            {totalExperience.toFixed(1)} / {maxTotalExperience}
          </span>
        </div>
      )}

      {/* TA bars */}
      <div className="flex flex-col gap-1.5">
        {Object.entries(taExperience).map(([ta, experience]) => {
          const config = TA_CONFIG[ta] || { label: ta, color: "bg-gray-500" };
          const percentage = maxTotalExperience
            ? Math.min((experience / maxTotalExperience) * 100, 100)
            : Math.min((experience / maxExperience) * 100, 100);

          return (
            <TooltipProvider key={ta}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2">
                    <span className="w-20 truncate text-xs text-gray-500">
                      {config.label}
                    </span>
                    <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`absolute left-0 top-0 h-full rounded-full transition-all duration-500 ${config.color}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-xs font-medium text-gray-600">
                      {experience.toFixed(1)}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p className="text-sm font-medium">{config.label}</p>
                  <p className="text-sm text-gray-500">
                    Experience: {experience.toFixed(1)}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          );
        })}
      </div>
    </div>
  );
}
