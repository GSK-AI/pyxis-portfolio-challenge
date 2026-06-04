"use client";

import { useHomeScreen } from "@/context/HomeScreenContext";
import { House } from "lucide-react";

export function HomeButton({ showNavbar }: { showNavbar: boolean }) {
  const { isHomeScreen } = useHomeScreen();

  if (showNavbar || isHomeScreen) return null;

  return (
    <div className="border-b border-gray-100 bg-white pb-2 pt-3">
      <div className="mx-auto px-4" style={{ maxWidth: "1560px" }}>
        <a
          href="/"
          className="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
        >
          <House className="h-4 w-4" />
          Home
        </a>
      </div>
    </div>
  );
}
