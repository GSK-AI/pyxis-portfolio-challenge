"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
import { AreaClosed, LinePath } from "@visx/shape";
import { curveLinear } from "@visx/curve";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { LinearGradient } from "@visx/gradient";
import type { AssetSchemaType } from "@/lib/definitionsGameZ";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  formatCurrency,
  formatDisplayNumber,
  formatNumber,
} from "@/lib/numbers";

/**
 * v2 asset detail dialog (classic AssetInfo data, new presentation):
 * description, metric grid, projected cost/budget spark areas in the
 * house chart style, and the clinical trials table.
 */

const STATE_STYLES: Record<string, string> = {
  Idle: "bg-secondary text-muted-foreground",
  "In Development": "bg-[#fff7e0] text-[#8a6d00]",
  "On Market": "bg-[#e8f6ec] text-[#2f7d3f]",
  Expired: "bg-secondary text-muted-foreground",
  Failed: "bg-destructive/10 text-destructive",
  Dropped: "bg-destructive/10 text-destructive",
};

const TICK = "#9aa0ab";
const MARGIN = { top: 8, right: 8, bottom: 22, left: 44 };

function SparkArea({
  data,
  color,
  id,
  height,
  width,
}: {
  data: number[];
  color: string;
  id: string;
  height: number;
  width: number;
}) {
  const points = data.map((value, time) => ({ time, value }));
  const maxValue = Math.max(10, ...data);
  const innerHeight = height - MARGIN.top - MARGIN.bottom;
  const xScale = scaleLinear({
    range: [MARGIN.left, width - MARGIN.right],
    domain: [0, Math.max(points.length - 1, 1)],
  });
  const yScale = scaleLinear({
    range: [innerHeight + MARGIN.top, MARGIN.top],
    domain: [0, maxValue * 1.15],
  });
  return (
    <svg width={width} height={height}>
      <LinearGradient
        id={id}
        from={color}
        to={color}
        fromOpacity={0.2}
        toOpacity={0.02}
      />
      <Group>
        <GridRows
          left={MARGIN.left}
          width={width - MARGIN.left - MARGIN.right}
          scale={yScale}
          numTicks={3}
          stroke="#000000"
          strokeOpacity={0.05}
        />
        <AreaClosed
          data={points}
          x={(d) => xScale(d.time)}
          y={(d) => yScale(d.value)}
          yScale={yScale}
          curve={curveLinear}
          fill={`url(#${id})`}
        />
        <LinePath
          data={points}
          x={(d) => xScale(d.time)}
          y={(d) => yScale(d.value)}
          stroke={color}
          strokeWidth={2}
          curve={curveLinear}
        />
        <AxisBottom
          top={innerHeight + MARGIN.top}
          scale={xScale}
          hideTicks
          stroke="#d5d7db"
          numTicks={5}
          tickLabelProps={() => ({
            fill: TICK,
            fontSize: 10,
            textAnchor: "middle",
          })}
        />
        <AxisLeft
          left={MARGIN.left}
          scale={yScale}
          tickFormat={(v) => formatDisplayNumber(Number(v))}
          numTicks={3}
          hideTicks
          hideAxisLine
          tickLabelProps={() => ({
            fill: TICK,
            fontSize: 10,
            textAnchor: "end",
            dx: "-0.25em",
            dy: "0.25em",
          })}
        />
      </Group>
    </svg>
  );
}

function Metric({
  label,
  value,
  emphasis = false,
  muted = false,
  title,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
  muted?: boolean;
  title?: string;
}) {
  return (
    <div title={title}>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
        {label}
      </div>
      <div
        className={cn(
          "mt-0.5 text-sm font-bold tabular-nums",
          emphasis && "text-primary",
          muted && "font-medium text-muted-foreground",
        )}
      >
        {value}
      </div>
    </div>
  );
}

const TH =
  "px-3 py-2 text-left text-xs font-medium tracking-wide text-muted-foreground whitespace-nowrap border-b border-foreground/10";
const TD = "px-3 py-2.5 text-sm align-middle whitespace-nowrap";

export default function AssetDetailDialog({
  asset,
  emphasizeCashValue = false,
  reinvestmentPercentage = 1,
  ptrsReadingsEnabled = false,
}: {
  asset: AssetSchemaType;
  emphasizeCashValue?: boolean;
  reinvestmentPercentage?: number;
  ptrsReadingsEnabled?: boolean;
}) {
  const [open, setOpen] = useState(false);

  // --- identical trial extraction to the classic AssetInfo ---
  const phaseNames = Object.keys(asset.trials);
  const trials = phaseNames.map((phase) => ({
    phase,
    ...asset.trials[phase as keyof typeof asset.trials],
  }));
  // --- end identical logic ---

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          aria-label={`About ${asset.name}`}
          className="inline-flex"
          onClick={(e) => e.stopPropagation()}
        >
          <Info className="size-4 cursor-pointer" />
        </button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto rounded font-light">
        <DialogHeader className="space-y-3 text-left">
          <DialogTitle className="flex items-center gap-2.5 text-lg font-bold tracking-tight">
            {asset.name}
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-bold",
                STATE_STYLES[asset.state] ??
                  "bg-secondary text-muted-foreground",
              )}
            >
              {asset.state}
            </span>
          </DialogTitle>
          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            {asset.description}
          </p>
        </DialogHeader>

        {/* Metrics */}
        <div className="grid grid-cols-4 gap-x-4 gap-y-4 rounded bg-secondary/25 p-4">
          <Metric
            label="Peak Year Sales"
            value={`£${formatDisplayNumber(asset.max_revenue)}`}
          />
          <Metric
            label="Launch → PYS"
            value={`${asset.time_until_max_revenue}y`}
          />
          <Metric
            label="Patent Expiry"
            value={`${asset.time_until_patent_expiry}y`}
          />
          <Metric
            label="On Market"
            value={asset.time_on_market > 0 ? `${asset.time_on_market}y` : "No"}
          />
          {emphasizeCashValue ? (
            <>
              <Metric
                label="Cash eNPV"
                value={formatCurrency(asset.cash_enpv)}
                emphasis
                title="eNPV with sales scaled by the reinvestment rate (35%)."
              />
              <Metric
                label="Business eNPV"
                value={formatCurrency(asset.enpv)}
                muted
                title="Full eNPV with sales unscaled. Context only."
              />
            </>
          ) : (
            <Metric label="eNPV" value={formatCurrency(asset.enpv)} />
          )}
          <Metric label="eROI" value={`x${asset.eroi.toFixed(1)}`} />
        </div>

        {/* Projections */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded bg-secondary/25 p-4">
            <div className="text-sm font-bold tracking-wide">
              Projected Costs
            </div>
            <div className="mt-3 h-[160px]">
              <ParentSize debounceTime={10}>
                {({ width }) =>
                  width > 0 ? (
                    <SparkArea
                      data={asset.expected_costs}
                      color="#3e71d2"
                      id={`cost-${asset.id}`}
                      width={width}
                      height={160}
                    />
                  ) : null
                }
              </ParentSize>
            </div>
          </div>
          <div className="rounded bg-secondary/25 p-4">
            <div className="text-sm font-bold tracking-wide">
              Projected Budget Contribution
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Only the reinvestment rate (35%) of sales reaches your Capital.
            </p>
            <div className="mt-2 h-[160px]">
              <ParentSize debounceTime={10}>
                {({ width }) =>
                  width > 0 ? (
                    <SparkArea
                      data={asset.expected_revenues.map(
                        (revenue) => revenue * reinvestmentPercentage,
                      )}
                      color="#15717d"
                      id={`budget-${asset.id}`}
                      width={width}
                      height={160}
                    />
                  ) : null
                }
              </ParentSize>
            </div>
          </div>
        </div>

        {/* Clinical trials */}
        <div>
          <div className="mb-2 text-sm font-bold tracking-wide">
            Clinical Trials
          </div>
          <div className="overflow-hidden rounded ring-1 ring-foreground/5">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className={TH}>Phase</th>
                  <th className={TH}>PTRS</th>
                  {ptrsReadingsEnabled && <th className={TH}>Eff. Readings</th>}
                  <th className={TH}>Remaining Time (y)</th>
                  <th className={cn(TH, "text-right")}>Remaining Cost</th>
                </tr>
              </thead>
              <tbody>
                {trials.length === 0 ? (
                  <tr>
                    <td
                      colSpan={ptrsReadingsEnabled ? 5 : 4}
                      className="px-3 py-6 text-center text-sm text-muted-foreground"
                    >
                      No trial data available.
                    </td>
                  </tr>
                ) : (
                  trials.map((trial, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-foreground/5 last:border-b-0"
                    >
                      <td className={cn(TD, "font-bold")}>{trial.phase}</td>
                      <td className={cn(TD, "tabular-nums")}>
                        {formatNumber(trial.ptrs ?? 0, 2)}
                      </td>
                      {ptrsReadingsEnabled && (
                        <td className={cn(TD, "tabular-nums")}>
                          {formatNumber(trial.ptrs_effective_readings ?? 0, 1)}
                        </td>
                      )}
                      <td className={cn(TD, "tabular-nums")}>
                        {trial.time_remaining ?? 0}
                      </td>
                      <td className={cn(TD, "text-right tabular-nums")}>
                        {formatDisplayNumber(trial.cost_remaining ?? 0)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
