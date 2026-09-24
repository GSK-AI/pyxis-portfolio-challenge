import { Fragment } from "react";
import { cn } from "@/lib/utils";
import { MoveDownRight, MoveUpRight } from "lucide-react";
import { InfoHint } from "./InfoHint";

export interface StatProps {
  label: string;
  value: string;
  delta?: { value: string; direction: "up" | "down" };
  size?: "md" | "lg";
  /** "danger" paints the value red (e.g. insufficient capital). */
  tone?: "danger";
  info?: { title: string; description: string };
  className?: string;
}

function DeltaLine({ delta }: { delta?: StatProps["delta"] }) {
  // The text is absolutely positioned inside the reserved row so a long
  // delta (e.g. "£19.3M committed this year") never widens the stat's
  // column — it overflows into the neighbours' empty delta row instead.
  return (
    <div className="relative min-h-5 text-sm">
      {delta && (
        <div
          className={cn(
            "absolute inset-y-0 left-0 flex items-center gap-1 whitespace-nowrap",
            delta.direction === "down" ? "text-destructive" : "text-chart-4",
          )}
        >
          {delta.direction === "down" ? (
            <MoveDownRight className="size-3.5" />
          ) : (
            <MoveUpRight className="size-3.5" />
          )}
          {delta.value}
        </div>
      )}
    </div>
  );
}

const valueClass = (size: StatProps["size"], tone?: StatProps["tone"]) =>
  cn(
    "font-bold tracking-tight",
    size === "lg" ? "text-4xl" : "text-2xl",
    tone === "danger" && "text-destructive",
  );

/**
 * Big number with a label and optional delta — Available Capital, eNPV, eROI.
 * For a ROW of stats use StatGroup, which baseline-aligns the values.
 */
export function Stat({
  label,
  value,
  delta,
  size = "md",
  tone,
  info,
  className,
}: StatProps) {
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center gap-1 text-sm text-muted-foreground">
        {label}
        {info && <InfoHint {...info} />}
      </div>
      <div className={valueClass(size, tone)}>{value}</div>
      <DeltaLine delta={delta} />
    </div>
  );
}

/**
 * Row of stats in one shared grid: labels on one line, values
 * baseline-aligned across different sizes, deltas underneath.
 */
export function StatGroup({
  stats,
  className,
  id,
}: {
  stats: StatProps[];
  className?: string;
  /** Anchor for the onboarding tour. */
  id?: string;
}) {
  return (
    // w-fit, not just justify-start: the columns already sit left with
    // justify-start, but the box itself would still stretch to the width of
    // whatever holds it — which the tour spotlight then highlights as a band
    // of empty space beside the numbers.
    <div
      id={id}
      className={cn("grid w-fit justify-start gap-x-10 gap-y-1", className)}
      style={{ gridAutoFlow: "column", gridTemplateRows: "auto auto auto" }}
    >
      {stats.map((stat, i) => (
        <Fragment key={i}>
          <div className="flex items-center gap-1 self-end text-sm text-muted-foreground">
            {stat.label}
            {stat.info && <InfoHint {...stat.info} />}
          </div>
          <div
            key={`${i}-${stat.value}`}
            className={cn(
              "v2-pop self-baseline",
              valueClass(stat.size, stat.tone),
            )}
          >
            {stat.value}
          </div>
          <DeltaLine delta={stat.delta} />
        </Fragment>
      ))}
    </div>
  );
}
