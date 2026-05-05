"use client";

import { ChartScatter, LayoutGrid, List } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function TheGridList({
  view,
  setView,
}: {
  view: "grid" | "list" | "frontier";
  setView: (view: "grid" | "list" | "frontier") => void;
}) {
  return (
    <div className="flex">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setView("list")}
        aria-label="List View"
        className={`rounded ${view === "list" ? "bg-primary text-white hover:bg-primary hover:text-white" : ""}`}
      >
        <List size={4} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => setView("grid")}
        aria-label="Grid View"
        className={`rounded ${view === "grid" ? "bg-primary text-white hover:bg-primary hover:text-white" : ""}`}
      >
        <LayoutGrid size={4} />
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={() => setView("frontier")}
        aria-label="Frontier"
        className={`ml-6 rounded ${view === "frontier" ? "bg-primary text-white hover:bg-primary hover:text-white" : ""}`}
      >
        <ChartScatter size={4} />
        Efficiency Frontier
      </Button>
    </div>
  );
}
