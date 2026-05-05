"use client";

import { useCallback } from "react";

export function useCustomNextStep() {
  const markTourSkipped = useCallback(
    (step: number, tourName: string | null) => {
      // Store tour skip information in localStorage - when skipped, mark all tours as skipped
      if (tourName) {
        const tourData = JSON.parse(localStorage.getItem("tourData") || "{}");
        tourData.allToursSkipped = true;
        tourData.skipTimestamp = new Date().toISOString();
        localStorage.setItem("tourData", JSON.stringify(tourData));
      }
    },
    [],
  );

  const markTourCompleted = useCallback((tourName: string | null) => {
    // Store tour completion information in localStorage
    if (tourName) {
      const tourData = JSON.parse(localStorage.getItem("tourData") || "{}");
      if (!tourData.completedTours) {
        tourData.completedTours = {};
      }
      tourData.completedTours[tourName] = {
        completed: true,
        timestamp: new Date().toISOString(),
      };
      localStorage.setItem("tourData", JSON.stringify(tourData));
    }
  }, []);

  const isTourSkipped = useCallback((): boolean => {
    const tourData = JSON.parse(localStorage.getItem("tourData") || "{}");
    return Boolean(tourData.allToursSkipped);
  }, []);

  const isTourCompleted = useCallback((tourName: string): boolean => {
    const tourData = JSON.parse(localStorage.getItem("tourData") || "{}");
    return Boolean(tourData.completedTours?.[tourName]?.completed);
  }, []);

  const shouldShowTour = useCallback(
    (tourName: string): boolean => {
      // Don't show if all tours are skipped
      if (isTourSkipped()) {
        return false;
      }
      // Don't show if this specific tour is completed
      if (isTourCompleted(tourName)) {
        return false;
      }
      return true;
    },
    [isTourSkipped, isTourCompleted],
  );

  const resetTourSkipStatus = useCallback(() => {
    const tourData = JSON.parse(localStorage.getItem("tourData") || "{}");
    tourData.allToursSkipped = false;
    delete tourData.skipTimestamp;
    localStorage.setItem("tourData", JSON.stringify(tourData));
  }, []);

  const resetTourCompletionStatus = useCallback((tourName: string) => {
    const tourData = JSON.parse(localStorage.getItem("tourData") || "{}");
    if (tourData.completedTours?.[tourName]) {
      delete tourData.completedTours[tourName];
      localStorage.setItem("tourData", JSON.stringify(tourData));
    }
  }, []);

  const clearAllTourData = useCallback(() => {
    localStorage.removeItem("tourData");
  }, []);

  const startTourIfNotSkipped = useCallback(
    (tourName: string, startNextStep: (tourName: string) => void) => {
      if (shouldShowTour(tourName)) {
        startNextStep(tourName);
      }
    },
    [shouldShowTour],
  );

  return {
    markTourSkipped,
    markTourCompleted,
    isTourSkipped,
    isTourCompleted,
    shouldShowTour,
    resetTourSkipStatus,
    resetTourCompletionStatus,
    clearAllTourData,
    startTourIfNotSkipped,
  };
}
