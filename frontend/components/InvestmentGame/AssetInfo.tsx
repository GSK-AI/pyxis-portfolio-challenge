import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Info } from "lucide-react";
import { AssetSchemaType } from "@/lib/definitionsGameZ";
import {
  formatDisplayNumber,
  formatNumber,
  formatCurrency,
} from "@/lib/numbers";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import { Badge } from "../ui/badge";
import ProjectedChart from "./ProjectedChart";

export default function AssetInfo({ asset }: { asset: AssetSchemaType }) {
  const [open, setOpen] = useState(false);
  // Extract phase names and trial data as pairs
  const phaseNames = Object.keys(asset.trials);
  const trials = phaseNames.map((phase) => ({
    phase,
    ...asset.trials[phase as keyof typeof asset.trials],
  }));

  // Only show unfinished trials for summary
  const unfinishedTrials = trials.filter(
    (trial) =>
      (trial.cost_remaining ?? 0) > 0 || (trial.time_remaining ?? 0) > 0,
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Info size={16} className="cursor-pointer" />
      </DialogTrigger>
      <DialogContent className="h-[90vh] max-h-[90vh] max-w-[900px] overflow-y-auto">
        <DialogTitle className="hidden"></DialogTitle>
        <DialogHeader>
          <div className="flex items-center gap-4">
            <h2 className="text-xl">Asset: {asset.name}</h2>
            <Badge className="px-2 py-1 text-sm capitalize">
              {asset.state}
            </Badge>
          </div>
          <p className={"mb-6 mt-2 max-w-lg text-sm font-light text-gray-600"}>
            {asset.description}
          </p>

          {/* 2-column layout: Info on left, Chart on right */}
          <div className="!my-4 grid grid-cols-3 gap-4">
            {/* Left column - Asset info */}
            <div className="flex flex-col gap-4 rounded-xl bg-gray-50 p-4 font-light">
              <span className="w-[60%] font-light">Peak Year Sales (PYS):</span>
              <strong>£{formatDisplayNumber(asset.max_revenue)}</strong>
            </div>
            <div className="flex flex-col gap-4 rounded-xl bg-gray-50 p-4 font-light">
              <span className="w-[60%] font-light">
                Time from launch until PYS:
              </span>
              <strong>{asset.time_until_max_revenue} years</strong>
            </div>
            <div className="flex flex-col gap-4 rounded-xl bg-gray-50 p-4 font-light">
              <span className="w-[60%] font-light">
                Time until patent expiry:
              </span>
              <strong>{asset.time_until_patent_expiry} years</strong>
            </div>
            <div className="flex flex-col gap-4 rounded-xl bg-gray-50 p-4 font-light">
              <span className="w-[60%] font-light">Time on market:</span>
              <strong>{asset.time_on_market} years</strong>
            </div>
            <div className="flex flex-col gap-4 rounded-xl bg-gray-50 p-4 font-light">
              <span className="w-[60%] font-light">On Market:</span>
              <strong>{asset.time_on_market > 0 ? "Yes" : "No"}</strong>
            </div>
            <div className="flex flex-col gap-4 rounded-xl bg-gray-50 p-4 font-light">
              <span className="w-[60%] font-light">eNPV:</span>
              <strong>{formatCurrency(asset.enpv)}</strong>
            </div>
            <div className="flex flex-col gap-4 rounded-xl bg-gray-50 p-4 font-light">
              <span className="w-[60%] font-light">eROI:</span>
              <strong>x{asset.eroi.toFixed(1)}</strong>
            </div>
          </div>

          {/* Right column - Chart */}
          <div className="flex gap-4">
            <div className="rounded-xl bg-gray-100 px-2 py-4">
              <h3 className="mb-4 text-lg">Projected Costs</h3>
              <ProjectedChart data={asset.expected_costs} dataType="cost" />
            </div>

            <div className="rounded-xl bg-gray-100 px-2 py-4">
              <h3 className="mb-4 text-lg">Projected Budget Contribution</h3>
              <ProjectedChart
                data={asset.expected_revenues}
                dataType="revenue"
              />
            </div>
          </div>

          <div>
            <h3 className="text-lg">Clinical Trials</h3>

            <div className="c-table my-6 w-full">
              <Table className="w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead>Phase</TableHead>
                    <TableHead>PTRS</TableHead>
                    <TableHead>Remaining Time (years)</TableHead>
                    <TableHead className="text-right">
                      Remaining Cost (£)
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trials.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center">
                        No trial data available.
                      </TableCell>
                    </TableRow>
                  ) : (
                    trials.map((trial, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{trial.phase}</TableCell>
                        <TableCell>
                          {formatNumber(trial.ptrs ?? 0, 2)}
                        </TableCell>
                        <TableCell>{trial.time_remaining ?? 0}</TableCell>
                        <TableCell className="text-right">
                          {formatDisplayNumber(trial.cost_remaining ?? 0)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            <div className="mt-4">
              <div className="flex justify-between font-medium">
                <span>Total Remaining Cost:</span>
                <span>
                  £
                  {unfinishedTrials.length > 0
                    ? formatDisplayNumber(
                        unfinishedTrials.reduce(
                          (acc, trial) => acc + (trial.cost_remaining ?? 0),
                          0,
                        ),
                      )
                    : 0}
                </span>
              </div>
              <div className="flex justify-between font-medium">
                <span>Total Remaining Time:</span>
                <span>
                  {unfinishedTrials.length > 0
                    ? unfinishedTrials.reduce(
                        (acc, trial) => acc + (trial.time_remaining ?? 0),
                        0,
                      )
                    : 0}{" "}
                  years
                </span>
              </div>
            </div>
          </div>
        </DialogHeader>
      </DialogContent>
    </Dialog>
  );
}
