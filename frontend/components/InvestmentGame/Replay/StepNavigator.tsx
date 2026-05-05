"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Timeline from "../Timeline";

interface StepNavigatorProps {
  currentStepIndex: number;
  totalSteps: number;
  onGoTo: (index: number) => void;
  onNext: () => void;
  onPrev: () => void;
}

export default function StepNavigator({
  currentStepIndex,
  totalSteps,
  onGoTo,
  onNext,
  onPrev,
}: StepNavigatorProps) {
  const displayValue = String(currentStepIndex);

  return (
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={onPrev}
        disabled={currentStepIndex <= 0}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      <div className="flex items-center gap-1">
        <span className="text-sm text-gray-500">Step</span>
        <Input
          className="h-8 w-16 text-center text-sm"
          value={displayValue}
          onChange={(e) => {
            const val = parseInt(e.target.value, 10);
            if (!isNaN(val)) {
              onGoTo(val);
            }
          }}
          onFocus={(e) => e.target.select()}
        />
        <span className="text-sm text-gray-500">/ {totalSteps - 1}</span>
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={onNext}
        disabled={currentStepIndex >= totalSteps - 1}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>

      <div className="ml-2 w-32">
        <Timeline currentTime={currentStepIndex} totalTime={totalSteps - 1} />
      </div>
    </div>
  );
}
