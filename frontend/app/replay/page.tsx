"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import FileUploadArea from "@/components/InvestmentGame/Replay/FileUploadArea";
import { ReplayExperienceV2 } from "@/components/v2/replay/ReplayExperienceV2";
import type { PlaythroughData } from "@/lib/definitionsGameZ";

export default function ReplayPage() {
  const [playthroughData, setPlaythroughData] =
    useState<PlaythroughData | null>(null);

  if (playthroughData) {
    return (
      <ReplayExperienceV2
        data={playthroughData}
        onExit={() => setPlaythroughData(null)}
      />
    );
  }

  return (
    <div className="-mb-4 -mt-6 font-light">
      <div className="relative mx-auto w-full max-w-[1920px] md:min-h-dvh">
        {/* Left: visual panel (mirrored vs. home so the page feels distinct).
            Absolutely placed at a fixed half so it never gets squeezed — the
            content column rides over it on narrower screens. */}
        <div className="absolute inset-y-0 left-0 hidden w-1/2 p-3 md:block">
          <div className="relative h-full min-h-[560px] overflow-hidden rounded bg-secondary">
            <div
              aria-hidden
              className="absolute inset-0 bg-[url('/images/tech-helix-color.webp')] bg-cover bg-center"
            />
          </div>
        </div>

        {/* Right: title + upload. Holds a floor width and overlaps the image
            once the viewport can't fit both side by side. */}
        <div className="relative flex flex-col p-8 sm:p-12 md:ml-auto md:min-h-dvh md:w-[max(50%,700px)] lg:px-16">
          {/* Glass: invisible over the white page, frosts the helix where the
              column overhangs it. Faded out at the overhanging edge (left
              here, mirroring the layout) so the panel has no hard seam. */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-background/85 backdrop-blur-sm"
            style={{
              maskImage: "linear-gradient(to left, black 92%, transparent)",
              WebkitMaskImage:
                "linear-gradient(to left, black 92%, transparent)",
            }}
          />
          <div className="relative">
            <Link href="/">
              <Image
                src="/images/pyxis-app-icon-2.svg"
                alt="Pyxis"
                width={44}
                height={44}
              />
            </Link>
          </div>

          <div className="relative flex flex-1 flex-col justify-center space-y-8 py-10">
            <div className="space-y-4">
              <h1 className="text-4xl leading-[1.1] tracking-tight sm:text-5xl">
                <span className="block font-normal">Watch a</span>
                <span className="block text-muted-foreground">Replay</span>
              </h1>
              <p className="text-base leading-relaxed text-muted-foreground">
                Load a playthrough file to explore a full game step by step —
                every decision, auction, and portfolio move.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">Upload</h2>
                <Link
                  href="/"
                  className="flex items-center gap-1.5 text-sm text-primary hover:underline"
                >
                  <ArrowLeft className="size-4" />
                  Back to Play
                </Link>
              </div>
              <FileUploadArea onPlaythroughLoaded={setPlaythroughData} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
