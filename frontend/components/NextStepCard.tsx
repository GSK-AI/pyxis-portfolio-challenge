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

/** True if the element or any ancestor is stuck to the viewport. */
function isPinned(el: Element) {
  for (let node: Element | null = el; node; node = node.parentElement) {
    const position = getComputedStyle(node).position;
    if (position === "sticky" || position === "fixed") return true;
  }
  return false;
}

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
      if (!el) return;

      // Sticky and fixed targets (the top bar and everything in it) don't
      // move when you scroll, so scrolling "to" them only drags the rest of
      // the page out from under the player. They're always on screen anyway.
      if (isPinned(el)) return;

      // scrollIntoView, not window.scrollTo: the v2 game screen is a fixed
      // -height shell that scrolls an inner container, so window scrolling
      // moves nothing. This works in whichever ancestor actually scrolls,
      // and still behaves on ordinary page-scrolled views.
      //
      // Centre anything that fits. Leaving an already-visible target alone
      // isn't enough — nextstep hangs the card outside the element it
      // highlights and clips whatever runs past the viewport, so a target
      // sitting near an edge needs moving even though you can see it.
      // Only targets too tall to centre fall back to nextstep's own block
      // choice: it re-scrolls those itself and measures the spotlight before
      // that smooth scroll lands, so matching its choice makes it a no-op.
      const side = targetStep?.side ?? "right";
      el.scrollIntoView({
        behavior: "instant",
        block:
          el.getBoundingClientRect().height <= window.innerHeight
            ? "center"
            : side.includes("top")
              ? "end"
              : "start",
      });
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
        {/* The arrow is a bare SVG filled with currentColor, so it picks up
            the body text colour and lands as a black wedge. It's meant to
            read as the card's own tail — paint it the card's background. */}
        <span className="text-card">{arrow}</span>
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
