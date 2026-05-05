import { formatDisplayNumber, formatCurrency } from "@/lib/numbers";
import type { AssetSchemaType, ActionType } from "@/lib/definitionsGameZ";
import { InformationButton } from "../InformationButton";
import { informationDictionary } from "@/lib/information-dictionary-game";
import {
  calculateExpectedNPV,
  calculateExpectedROI,
  calculateAvailableCapital,
  calculateCapitalChange,
  hasCapitalChange,
  isInsufficientCapital,
  calculateEnpvChange,
  calculateEroiChange,
  hasEnpvChange,
  hasEroiChange,
} from "@/lib/investment-game-calculations";

interface ActionStatsProps {
  time: number;
  startingCash: number;
  previousCash?: number;
  previousAssets?: AssetSchemaType[];
  cashInPot: number;
  assets: AssetSchemaType[];
  selection: Record<string, ActionType | boolean>;
  nextStepCost?: number; // Cost for next step from ActionChart
  taExperience?: Record<string, number>; // TA experience for uncertain PTRS
}

export default function ActionStats({
  time,
  startingCash,
  previousCash,
  previousAssets,
  cashInPot,
  assets,
  selection,
  nextStepCost,
}: ActionStatsProps) {
  const expectedNPV = calculateExpectedNPV(assets, selection);
  const expectedROI = calculateExpectedROI(assets, selection);
  const hasSelectedAssets = Object.values(selection).some(Boolean);

  // Calculate capital-related values
  const availableCapital = calculateAvailableCapital(
    startingCash,
    nextStepCost,
  );
  const capitalChange = calculateCapitalChange(startingCash, previousCash);
  const showCapitalChange = hasCapitalChange(previousCash, capitalChange);
  const insufficientCapital = isInsufficientCapital(startingCash, nextStepCost);

  // Calculate changes in eNPV and eROI
  const enpvChange = calculateEnpvChange(
    expectedNPV,
    previousAssets,
    selection,
  );
  const eroiChange = calculateEroiChange(
    expectedROI,
    previousAssets,
    selection,
  );
  const showEnpvChange = hasEnpvChange(time, enpvChange, previousAssets);
  const showEroiChange = hasEroiChange(time, eroiChange, previousAssets);

  return (
    <div
      className="flex min-w-[200px] flex-col items-start justify-between bg-gray-50/50"
      // id="actionStat"
    >
      {/* Stats Section - Fixed height to match ActionChart (200px) */}
      <div className="flex h-[215px] w-full gap-6 px-10 py-4">
        {/* Capital Column */}
        <div className="flex flex-1 flex-col justify-center">
          <div className="flex flex-col gap-1 text-right">
            <span className="whitespace-nowrap font-light text-gray-600">
              Available Capital
            </span>
            <strong
              className={`text-3xl font-light ${insufficientCapital ? "text-red-500" : "text-black"}`}
            >
              £{formatDisplayNumber(availableCapital)}
            </strong>
            {showCapitalChange && (
              <div className="flex justify-end">
                <div
                  className={`inline-flex w-fit items-center gap-1 whitespace-nowrap rounded-md text-sm font-medium ${
                    capitalChange >= 0 ? "text-green-600" : "text-red-600"
                  }`}
                >
                  <span className="text-xs">
                    {capitalChange >= 0 ? "↗" : "↘"}
                  </span>
                  <span>
                    {capitalChange >= 0 ? "+" : ""}£
                    {formatDisplayNumber(Math.abs(capitalChange))}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* eNPV & eROI Stacked Column */}
        <div className="flex flex-1 flex-col justify-center gap-6 pl-10">
          <div className="flex flex-col gap-1 text-right">
            <div className="flex items-center justify-end gap-0">
              <span className="font-light text-gray-600">eNPV</span>
              <div>
                <InformationButton
                  title={informationDictionary.eNPV.title}
                  description={informationDictionary.eNPV.description}
                  buttonClassName="w-4 h-4"
                />
              </div>
            </div>
            <div className="mr-1 flex flex-col gap-1 text-right">
              <strong
                className={`text-xl font-light ${expectedNPV < 0 ? "text-red-500" : "text-black"}`}
              >
                {formatCurrency(expectedNPV)}
              </strong>
              {showEnpvChange && (
                <div className="flex justify-end">
                  <div
                    className={`inline-flex w-fit items-center gap-1 whitespace-nowrap rounded-md text-sm font-medium ${
                      enpvChange >= 0 ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {/* <span className="text-xs">
                      {enpvChange >= 0 ? "↗" : "↘"}
                    </span>
                    <span>
                      {enpvChange >= 0 ? "+" : ""}
                      {formatCurrency(Math.abs(enpvChange))}
                    </span> */}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1 text-right">
            <div className="flex items-center justify-end gap-0">
              <span className="font-light text-gray-600">eROI</span>
              <InformationButton
                title={informationDictionary.eROI.title}
                description={informationDictionary.eROI.description}
                buttonClassName="w-4 h-4"
              />
            </div>
            <div className="mr-1 flex flex-col gap-1 text-right">
              <strong
                className={`text-xl font-light ${expectedROI < 0 ? "text-red-500" : "text-black"}`}
              >
                {"x" + expectedROI.toFixed(1)}
                {/* {hasSelectedAssets ? "x" + expectedROI.toFixed(1) : "--"} */}
              </strong>
              {showEroiChange && (
                <div className="flex justify-end">
                  <div
                    className={`inline-flex w-fit items-center gap-1 whitespace-nowrap rounded-md text-sm font-medium ${
                      eroiChange >= 0 ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {/* <span className="text-xs">
                      {eroiChange >= 0 ? "↗" : "↘"}
                    </span>
                    <span>
                      {eroiChange >= 0 ? "+" : "-"}
                      {Math.abs(eroiChange).toFixed(1)}
                    </span> */}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
