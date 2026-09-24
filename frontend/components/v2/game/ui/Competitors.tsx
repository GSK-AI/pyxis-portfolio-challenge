import { CircleCheck, Loader2, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDisplayNumber } from "@/lib/numbers";

/** Rank pill — trophy + amber for 1st, quiet grey otherwise. */
export function RankBadge({ rank }: { rank: number }) {
  const suffix =
    rank === 1 ? "st" : rank === 2 ? "nd" : rank === 3 ? "rd" : "th";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold",
        rank === 1
          ? "bg-[#dff4f8] text-[#15717d]"
          : "bg-secondary text-muted-foreground",
      )}
    >
      {rank === 1 && <Trophy className="size-3" />}
      {rank}
      {suffix}
    </span>
  );
}

function Metric({
  label,
  value,
  signed = false,
}: {
  label: string;
  value: number;
  signed?: boolean;
}) {
  return (
    <div>
      <div className="whitespace-nowrap text-[10px] uppercase tracking-wider text-muted-foreground/70">
        {label}
      </div>
      <div
        className={cn(
          "text-sm font-bold tabular-nums",
          signed && value < 0 && "text-destructive",
        )}
      >
        {formatDisplayNumber(value)}
      </div>
    </div>
  );
}

export interface CompetitorInfo {
  name: string;
  agentType: string;
  rank: number;
  ready?: boolean;
  netCashFlow: number;
  cash: number;
  onMarket: number;
  inDev: number;
  enpv: number;
  /** Out of the game before the horizon (classic red card + label). */
  bankrupt?: boolean;
  /** Renders the card as the player's own standing row. */
  isPlayer?: boolean;
}

export function CompetitorCard({
  name,
  agentType,
  rank,
  ready = false,
  netCashFlow,
  cash,
  onMarket,
  inDev,
  enpv,
  bankrupt = false,
  isPlayer = false,
  className,
}: CompetitorInfo & { className?: string }) {
  return (
    <div
      className={cn(
        "space-y-3 rounded p-4",
        className,
        bankrupt
          ? "bg-gradient-to-r from-[#fdf1f0] to-[#fdf8f7]"
          : isPlayer
            ? "bg-gradient-to-r from-[#e2edfb] to-[#f4f8fd]"
            : "bg-gradient-to-r from-[#f1f6fd] to-white",
      )}
    >
      <div className="flex items-center gap-2">
        <RankBadge rank={rank} />
        <span className="text-sm font-bold">{name}</span>
        {isPlayer ? (
          <span className="rounded-full bg-card px-2 py-0.5 text-xs font-bold text-primary">
            You
          </span>
        ) : (
          <>
            <span className="text-xs text-muted-foreground">{agentType}</span>
            {bankrupt ? (
              <span className="text-[10px] font-bold uppercase tracking-wider text-destructive">
                Bankrupt
              </span>
            ) : (
              <span
                title={ready ? "Ready" : "Thinking"}
                className="inline-flex"
              >
                {ready ? (
                  <CircleCheck className="size-4 text-[#2f9d55]" />
                ) : (
                  <Loader2 className="size-4 animate-spin text-muted-foreground/50" />
                )}
              </span>
            )}
          </>
        )}
      </div>
      <div className="flex items-baseline justify-between gap-4">
        <Metric label="Net Cash" value={netCashFlow} signed />
        <Metric label="Cash" value={cash} />
        <Metric label="eNPV" value={enpv} />
        <div>
          <div className="whitespace-nowrap text-[10px] uppercase tracking-wider text-muted-foreground/70">
            On Market
          </div>
          <div className="text-sm font-bold tabular-nums">{onMarket}</div>
        </div>
        <div>
          <div className="whitespace-nowrap text-[10px] uppercase tracking-wider text-muted-foreground/70">
            In Dev
          </div>
          <div className="text-sm font-bold tabular-nums">{inDev}</div>
        </div>
      </div>
    </div>
  );
}
