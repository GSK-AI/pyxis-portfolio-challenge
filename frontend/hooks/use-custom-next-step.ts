"use client";

import { useCallback } from "react";

const COOKIE_NAME = "tourData";
const COOKIE_DAYS = 365;

function readCookie(): Record<string, unknown> {
  try {
    const match = document.cookie.match(
      new RegExp("(?:^|; )" + COOKIE_NAME + "=([^;]*)"),
    );
    if (!match) return {};
    return JSON.parse(decodeURIComponent(match[1]));
  } catch {
    return {};
  }
}

function writeCookie(data: Record<string, unknown>) {
  try {
    const expires = new Date(Date.now() + COOKIE_DAYS * 864e5).toUTCString();
    document.cookie = `${COOKIE_NAME}=${encodeURIComponent(JSON.stringify(data))}; expires=${expires}; path=/; SameSite=None; Secure`;
  } catch {
    // Cookie access blocked (e.g. Safari cross-origin iframe) — fail silently
  }
}

function deleteCookie() {
  try {
    document.cookie = `${COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=None; Secure`;
  } catch {
    // ignore
  }
}

export function useCustomNextStep() {
  const markTourSkipped = useCallback(
    (step: number, tourName: string | null) => {
      if (tourName) {
        const data = readCookie();
        data.allToursSkipped = true;
        data.skipTimestamp = new Date().toISOString();
        writeCookie(data);
      }
    },
    [],
  );

  const markTourCompleted = useCallback((tourName: string | null) => {
    if (tourName) {
      const data = readCookie();
      if (!data.completedTours) data.completedTours = {};
      (data.completedTours as Record<string, unknown>)[tourName] = {
        completed: true,
        timestamp: new Date().toISOString(),
      };
      writeCookie(data);
    }
  }, []);

  const isTourSkipped = useCallback((): boolean => {
    return Boolean(readCookie().allToursSkipped);
  }, []);

  const isTourCompleted = useCallback((tourName: string): boolean => {
    const data = readCookie();
    return Boolean(
      (
        data.completedTours as
          | Record<string, { completed: boolean }>
          | undefined
      )?.[tourName]?.completed,
    );
  }, []);

  const shouldShowTour = useCallback(
    (tourName: string): boolean => {
      if (isTourSkipped()) return false;
      if (isTourCompleted(tourName)) return false;
      return true;
    },
    [isTourSkipped, isTourCompleted],
  );

  const resetTourSkipStatus = useCallback(() => {
    const data = readCookie();
    data.allToursSkipped = false;
    delete data.skipTimestamp;
    writeCookie(data);
  }, []);

  const resetTourCompletionStatus = useCallback((tourName: string) => {
    const data = readCookie();
    const completed = data.completedTours as Record<string, unknown> | undefined;
    if (completed?.[tourName]) {
      delete completed[tourName];
      writeCookie(data);
    }
  }, []);

  const clearAllTourData = useCallback(() => {
    deleteCookie();
  }, []);

  const startTourIfNotSkipped = useCallback(
    (tourName: string, startNextStep: (tourName: string) => void) => {
      if (shouldShowTour(tourName)) {
        markTourCompleted(tourName);
        startNextStep(tourName);
      }
    },
    [shouldShowTour, markTourCompleted],
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
