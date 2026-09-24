"use client";

import Image from "next/image";
import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

/**
 * v2 splash pattern: app icon + bold title + thin status line + pulsing
 * skeleton bar, centered directly on a faint helix/gradient backdrop
 * (no card). Colors come from the .ui-v2 token overrides in theme-v2.css.
 */

export function SplashCardV2({ children }: { children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center overflow-hidden bg-background font-light text-foreground">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[url('/images/tech-helix.jpg')] bg-cover bg-right opacity-5"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/10 via-transparent to-transparent"
      />
      <div className="relative flex flex-col items-center p-10">{children}</div>
    </div>
  );
}

export function SplashHeader({ statusLine }: { statusLine: string }) {
  return (
    <div className="flex items-center gap-4">
      <Image
        src="/images/pyxis-app-icon-2.svg"
        alt="Pyxis"
        width={50}
        height={50}
      />
      <div>
        <h1 className="text-lg font-bold tracking-wide">
          Pyxis Portfolio Challenge
        </h1>
        <p className="font-thin text-muted-foreground">{statusLine}</p>
      </div>
    </div>
  );
}

export function AuthSplashV2() {
  return (
    <SplashCardV2>
      <SplashHeader statusLine="Authenticating user, please wait..." />
      <div className="mt-6">
        <div className="h-5 w-[400px] animate-pulse rounded-md bg-muted" />
      </div>
    </SplashCardV2>
  );
}

export function ConnectionSplashV2({
  status,
}: {
  status: "loading" | "error";
}) {
  return (
    <SplashCardV2>
      <SplashHeader
        statusLine={
          status === "error"
            ? "Connection failed"
            : "Connecting, please wait..."
        }
      />
      <div className="mt-6">
        {status === "loading" && (
          <div className="h-5 w-[400px] animate-pulse rounded-md bg-muted" />
        )}
        {status === "error" && (
          <div className="max-w-[600px] rounded bg-destructive/5 px-3 py-1.5 text-destructive">
            <div className="flex items-start gap-2">
              <TriangleAlert className="mt-[5px] size-4 shrink-0" />
              <span>
                We apologize for the inconvenience. Please try again shortly,
                and if the issue persists, contact your application
                administrator for assistance.
              </span>
            </div>
          </div>
        )}
      </div>
    </SplashCardV2>
  );
}

export function AuthErrorSplashV2({ errorMsg }: { errorMsg: string }) {
  return (
    <SplashCardV2>
      <SplashHeader statusLine="Authentication failed" />
      <div className="mt-6 rounded bg-destructive/5 px-3 py-1.5 text-destructive">
        <div className="flex items-start gap-2">
          <TriangleAlert className="mt-[5px] size-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      </div>
    </SplashCardV2>
  );
}
