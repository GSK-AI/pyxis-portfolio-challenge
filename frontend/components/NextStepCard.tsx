"use client";

import React from "react";
import { Step, useNextStep } from "nextstepjs";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import steps from "@/lib/tours/gameOnboarding";

interface NextStepCardProps {
  step: Step;
  currentStep: number;
  totalSteps: number;
  nextStep: () => void;
  prevStep: () => void;
  skipTour?: () => void;
  arrow: React.ReactNode;
}

export default function NextStepCard({
  step,
  currentStep,
  totalSteps,
  nextStep,
  prevStep,
  skipTour,
  arrow,
}: NextStepCardProps) {
  const { currentTour } = useNextStep();

  const scrollToStep = (stepIndex: number) => {
    const tourConfig = steps.find((t) => t.tour === currentTour);
    const targetStep = tourConfig?.steps[stepIndex];
    const selector = targetStep?.selector;

    if (selector) {
      const el = document.querySelector(selector);
      if (el) {
        const rect = el.getBoundingClientRect();
        const center = window.scrollY + rect.top + rect.height / 2 - window.innerHeight / 2;
        window.scrollTo({ top: Math.max(0, center), behavior: "instant" });
      }
    } else {
      window.scrollTo({ top: 0, behavior: "instant" });
    }
  };

  const handleNext = () => {
    scrollToStep(currentStep + 1);
    nextStep();
  };

  const handlePrev = () => {
    scrollToStep(currentStep - 1);
    prevStep();
  };

  return (
    <Card className="w-[450px]">
      <CardHeader>
        <Progress
          value={((currentStep + 1) / totalSteps) * 100}
          className="mb-4 h-2"
        />
        <CardTitle className="flex items-center gap-2">{step.title}</CardTitle>
      </CardHeader>

      <CardContent>
        <div className="mb-2">{step.content}</div>
        {arrow}
      </CardContent>

      <CardFooter className="flex justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground">
            {currentStep + 1} / {totalSteps}
          </div>

          {step.showSkip && (
            <Button variant="ghost" size="sm" onClick={skipTour}>
              Skip
            </Button>
          )}
        </div>

        <div className="flex gap-2">
          {currentStep > 0 && (
            <Button variant="outline" size="sm" onClick={handlePrev}>
              Previous
            </Button>
          )}

          <Button size="sm" onClick={handleNext}>
            {currentStep === totalSteps - 1 ? "Finish" : "Next"}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
