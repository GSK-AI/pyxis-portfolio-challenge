"use client";

import { useState } from "react";
import { ArrowRight, Gamepad2 } from "lucide-react";
import LayoutContainer from "@/components/LayoutContainer";
import TheTitle from "@/components/TheTitle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { startGame, getCustomSeed } from "@/lib/backendCallsGame";

import type {
  GameStart,
  GameStepResponse,
  GameLevel,
} from "@/lib/definitionsGameZ";

export default function StartGame({
  handleStartGameCallback,
  setCustomStart,
}: {
  handleStartGameCallback: (obj: GameStepResponse, level?: GameLevel) => void;
  setCustomStart: (value: boolean) => void;
}) {
  // TODO: Defaults from API
  const [form, setForm] = useState<GameStart>({
    num_assets: 20,
    horizon: 5,
    starting_cash: 1000000,
    level_idx: -1,
    max_num_assets: 25,
    global_seed: 1,
  });
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string>("");
  const [validationErrors, setValidationErrors] = useState<{
    [key: string]: string;
  }>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;

    // Validate num_assets range
    if (name === "num_assets") {
      const numValue = parseInt(value, 10);
      if (numValue < 10 || numValue > 20) {
        setValidationErrors((prev) => ({
          ...prev,
          num_assets: "Number of assets must be between 10 and 20.",
        }));
      } else {
        setValidationErrors((prev) => ({ ...prev, num_assets: "" }));
      }
    }

    // Validate horizon range
    if (name === "horizon") {
      const numValue = parseInt(value, 10);
      if (numValue < 1 || numValue > 20) {
        setValidationErrors((prev) => ({
          ...prev,
          horizon: "Number of years must be between 1 and 20.",
        }));
      } else {
        setValidationErrors((prev) => ({ ...prev, horizon: "" }));
      }
    }

    // Validate starting_cash range
    if (name === "starting_cash") {
      const numValue = parseInt(value, 10);
      if (numValue > 100000000000) {
        setValidationErrors((prev) => ({
          ...prev,
          starting_cash: "Starting cash must be 100 billion or less.",
        }));
      } else {
        setValidationErrors((prev) => ({ ...prev, starting_cash: "" }));
      }
    }

    setForm((prev) => ({ ...prev, [name]: value }));
  };

  async function handleStartGame() {
    setStarting(true);
    setError(""); // Clear any previous errors
    try {
      // Get custom seed based on number of assets
      const customSeed = await getCustomSeed(form.num_assets);
      // Update form with the custom seed
      const updatedForm = { ...form, global_seed: customSeed };
      const response = await startGame(updatedForm);
      setStarting(false);
      handleStartGameCallback(response);
    } catch (err) {
      console.error(err);
      setStarting(false);
      setError("Failed to start the game. Please try again.");
    }
  }

  return (
    <div className="mt-6 px-6">
      <LayoutContainer className="c-splash-screen flex min-h-[75vh] gap-12 rounded-2xl bg-gray-800 !p-8 text-white">
        <div className="relative z-20 flex flex-1 items-center rounded-2xl bg-white p-20 text-black">
          <div className="space-y-10">
            <div>
              <div>
                <Gamepad2 />
              </div>
            </div>
            <h2 className="text-3xl">Start the Game</h2>

            {/* Form */}
            <div className="space-y-4">
              <div className="space-y-1">
                <div className="flex items-center gap-10">
                  <label htmlFor="num_assets" className="min-w-[200px]">
                    Number of Assets
                  </label>
                  <Input
                    type="number"
                    name="num_assets"
                    value={form.num_assets}
                    onChange={handleChange}
                    placeholder="Enter Number of assets"
                    max={20}
                    min={10}
                  />
                </div>
                {validationErrors.num_assets ? (
                  <p className="ml-[240px] text-xs text-red-600">
                    {validationErrors.num_assets}
                  </p>
                ) : (
                  <p className="ml-[240px] text-xs text-gray-400">
                    Range: 10-20
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-10">
                  <label htmlFor="horizon" className="min-w-[200px]">
                    Number of Years
                  </label>
                  <Input
                    type="number"
                    name="horizon"
                    value={form.horizon}
                    onChange={handleChange}
                    placeholder="Enter Number of Years"
                    max={20}
                    min={1}
                  />
                </div>
                {validationErrors.horizon ? (
                  <p className="ml-[240px] text-xs text-red-600">
                    {validationErrors.horizon}
                  </p>
                ) : (
                  <p className="ml-[240px] text-xs text-gray-400">
                    Range: 1-20
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-10">
                  <label htmlFor="starting_cash" className="min-w-[200px]">
                    Starting Cash
                  </label>
                  <Input
                    type="number"
                    name="starting_cash"
                    value={form.starting_cash}
                    onChange={handleChange}
                    placeholder="Enter Starting Cash"
                    max={100000000000}
                  />
                </div>
                {validationErrors.starting_cash ? (
                  <p className="ml-[240px] text-xs text-red-600">
                    {validationErrors.starting_cash}
                  </p>
                ) : (
                  <p className="ml-[240px] text-xs text-gray-400">
                    Max: 100 billion
                  </p>
                )}
              </div>
            </div>

            {/* Controls */}
            <div className="flex" onClick={handleStartGame}>
              <Button disabled={starting}>
                {starting ? "Starting" : "Start"} <ArrowRight />
              </Button>
            </div>

            {/* Error Message */}
            {error && <p className="text-sm text-red-600">{error}</p>}

            <div className="mt-4">
              <div
                onClick={() => setCustomStart(false)}
                className="cursor-pointer text-sm font-light text-blue-600 hover:text-blue-800"
              >
                → Return to Levels
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-1 items-end justify-between pb-20">
          <div>
            <TheTitle>Welcome to the Investment Game</TheTitle>
            <p className="font-light">Select your starting settings to play</p>
          </div>
        </div>
      </LayoutContainer>
    </div>
  );
}
