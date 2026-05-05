"use client";

import type { ViewMode } from "./useReplayState";

interface ViewModeToggleProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  disabled?: boolean;
}

export default function ViewModeToggle({
  viewMode,
  onViewModeChange,
  disabled = false,
}: ViewModeToggleProps) {
  return (
    <div className="inline-flex rounded-lg border border-gray-200 bg-gray-100 p-0.5">
      <button
        className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
          viewMode === "state"
            ? "bg-white text-gray-900 shadow-sm"
            : "text-gray-500 hover:text-gray-700"
        }`}
        onClick={() => onViewModeChange("state")}
      >
        State
      </button>
      <button
        className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
          viewMode === "action"
            ? "bg-white text-gray-900 shadow-sm"
            : disabled
              ? "cursor-not-allowed text-gray-300"
              : "text-gray-500 hover:text-gray-700"
        }`}
        onClick={() => !disabled && onViewModeChange("action")}
        disabled={disabled}
      >
        Actions
      </button>
    </div>
  );
}
