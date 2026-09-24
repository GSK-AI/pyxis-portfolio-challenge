import { Monitor } from "lucide-react";
import { SplashCardV2, SplashHeader } from "@/components/v2/SplashScreenV2";

/**
 * Below 1024px the app is replaced by a notice rather than reflowed — the
 * dashboard grid, boards panel and asset table all need that width before
 * they stop overlapping. Dressed as a v2 splash (icon + title + status line
 * on the helix backdrop) so the narrow-screen landing looks like the rest
 * of the app instead of an error page.
 *
 * Hidden via `hidden lg:contents` rather than conditional rendering, so
 * nothing unmounts and an in-progress game survives a resize or rotate.
 */
export function DesktopGate({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="lg:hidden">
        <SplashCardV2>
          <SplashHeader statusLine="This screen is too narrow" />
          <div className="mt-6 flex max-w-sm items-start gap-2.5 rounded bg-[var(--accent-soft)] px-3 py-2.5 text-sm text-muted-foreground">
            <Monitor className="mt-[3px] size-4 shrink-0 text-primary" />
            <span>
              Pyxis needs at least{" "}
              <span className="font-bold text-foreground">1024px</span> of
              width. Rotate your device, widen the window, or open this page on
              a desktop or laptop.
            </span>
          </div>
        </SplashCardV2>
      </div>

      <div className="hidden lg:contents">{children}</div>
    </>
  );
}
