"use client";

import { InformationButton } from "../InformationButton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface RDCapacityProps {
  capacityUsed: number;
  capacityBase: number;
  successModifier?: number;
  costModifier?: number;
}

export default function RDCapacity({
  capacityUsed,
  capacityBase,
  successModifier = 1.0,
  costModifier = 1.0,
}: RDCapacityProps) {
  const capacityRatio = capacityBase > 0 ? capacityUsed / capacityBase : 0;
  const percentage = Math.min(capacityRatio * 100, 150); // Cap display at 150%
  const isOverCapacity = capacityUsed > capacityBase;
  const hasPenalty = successModifier < 1.0 || costModifier > 1.0;

  // Color based on capacity usage
  const getBarColor = () => {
    if (capacityRatio > 1.2) return "bg-red-500";
    if (capacityRatio > 1.0) return "bg-orange-500";
    if (capacityRatio > 0.8) return "bg-yellow-500";
    return "bg-teal-500";
  };

  // Background color for the overflow area
  const getOverflowBgColor = () => {
    if (capacityRatio > 1.0) return "bg-red-100";
    return "bg-gray-200";
  };

  return (
    <div className="w-full rounded-lg bg-gray-50 p-2">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <span className="text-xs font-medium text-gray-600">
            R&D Capacity
          </span>
          <InformationButton
            title="R&D Capacity"
            description="Your research and development capacity determines how many trials you can run efficiently. Going over capacity increases costs and reduces success rates. Different investment levels (minimal, standard, accelerated) use different amounts of capacity."
            buttonClassName="w-3 h-3"
          />
        </div>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                className={`text-xs ${isOverCapacity ? "font-medium text-red-600" : "text-gray-500"}`}
              >
                {capacityUsed.toFixed(0)} / {capacityBase.toFixed(0)}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <div className="space-y-1 text-sm">
                <p>Capacity usage: {(capacityRatio * 100).toFixed(0)}%</p>
                {hasPenalty && (
                  <>
                    {successModifier < 1.0 && (
                      <p className="text-red-500">
                        Success rate: {(successModifier * 100).toFixed(0)}% of
                        normal
                      </p>
                    )}
                    {costModifier > 1.0 && (
                      <p className="text-orange-500">
                        Cost multiplier: {costModifier.toFixed(2)}x
                      </p>
                    )}
                  </>
                )}
                {!hasPenalty && !isOverCapacity && (
                  <p className="text-green-600">
                    Operating within capacity - no penalties
                  </p>
                )}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Capacity bar */}
      <div className="relative">
        <div
          className={`h-3 w-full overflow-hidden rounded-full ${getOverflowBgColor()}`}
        >
          {/* The 100% marker */}
          {isOverCapacity && (
            <div
              className="absolute top-0 z-10 h-3 w-0.5 bg-gray-400"
              style={{ left: `${(100 / 150) * 100}%` }}
            />
          )}
          {/* The fill bar */}
          <div
            className={`h-full rounded-full transition-all duration-500 ${getBarColor()}`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
          {/* Overflow portion */}
          {isOverCapacity && (
            <div
              className={`absolute top-0 h-full rounded-r-full transition-all duration-500 ${getBarColor()} opacity-70`}
              style={{
                left: `${(100 / 150) * 100}%`,
                width: `${Math.min((capacityRatio - 1) * 100, 50) * (100 / 150)}%`,
              }}
            />
          )}
        </div>
      </div>

      {/* Penalty indicators */}
      {hasPenalty && (
        <div className="mt-2 flex gap-2 text-xs">
          {successModifier < 1.0 && (
            <span className="rounded bg-red-100 px-1.5 py-0.5 text-red-700">
              -{((1 - successModifier) * 100).toFixed(0)}% success
            </span>
          )}
          {costModifier > 1.0 && (
            <span className="rounded bg-orange-100 px-1.5 py-0.5 text-orange-700">
              +{((costModifier - 1) * 100).toFixed(0)}% cost
            </span>
          )}
        </div>
      )}
    </div>
  );
}
