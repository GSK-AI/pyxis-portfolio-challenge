"use client";

import { NextStepProvider, NextStep } from "nextstepjs";
import steps from "@/lib/tours/gameOnboarding";
import NextStepCard from "./NextStepCard";
import { useCustomNextStep } from "@/hooks/use-custom-next-step";

interface NextStepClientProps {
  children: React.ReactNode;
}

export function NextStepClient({ children }: NextStepClientProps) {
  const { markTourSkipped, markTourCompleted } = useCustomNextStep();

  return (
    <NextStepProvider>
      <NextStep
        steps={steps}
        cardComponent={NextStepCard}
        onSkip={markTourSkipped}
        onComplete={markTourCompleted}
        noInViewScroll={true}
        scrollToTop={false}
      >
        {children}
      </NextStep>
    </NextStepProvider>
  );
}
