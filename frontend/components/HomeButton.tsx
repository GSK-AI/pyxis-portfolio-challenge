"use client";

import { useHomeScreen } from "@/context/HomeScreenContext";
import { House } from "lucide-react";

export function HomeButton({ showNavbar }: { showNavbar: boolean }) {
  const { isHomeScreen } = useHomeScreen();

  if (showNavbar || isHomeScreen) return null;

  return (
    <div className="px-4 pt-4">
      <a
        href="/"
        className="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
      >
        <House className="h-4 w-4" />
        Home
      </a>
    </div>
  );
}
