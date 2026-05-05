"use client";

import { useRouter, usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { HelpCircle } from "lucide-react";
import { useCustomNextStep } from "@/hooks/use-custom-next-step";
import { dispatchCustomEvent } from "@/lib/utils";

export function StartOnboardingTour() {
  const { clearAllTourData } = useCustomNextStep();
  const router = useRouter();
  const pathname = usePathname();

  const handleStartTour = () => {
    // Clear all tour data to reset storage
    clearAllTourData();

    // Check if already on investment-game route
    if (pathname === "/") {
      // Already on the route, dispatch event to start tour
      dispatchCustomEvent("startOnboardingTour", { tourName: "startScreen" });
    } else {
      // Navigate to the start screen first
      router.push("/");

      // Dispatch event after navigation (the page will listen for this)
      setTimeout(() => {
        dispatchCustomEvent("startOnboardingTour", { tourName: "startScreen" });
      }, 100);
    }
  };

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={handleStartTour}
      className="ml-10 flex items-center gap-2"
    >
      <HelpCircle className="h-4 w-4" />
      Start Tour
    </Button>
  );
}
