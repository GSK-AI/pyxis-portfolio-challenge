"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

/**
 * iPad-style scroll region: hidden scrollbars with native momentum, and
 * gradient fades at the edges while more content remains in that
 * direction. Background-matched to the card surface.
 */
export function FadeScroll({
  children,
  className,
}: {
  children: ReactNode;
  /** Sizing for the scroll region, e.g. "max-h-[380px]". */
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [fade, setFade] = useState({ top: false, bottom: false });

  const update = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    setFade({
      top: el.scrollTop > 1,
      bottom: el.scrollTop + el.clientHeight < el.scrollHeight - 1,
    });
  }, []);

  useEffect(() => {
    update();
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [update, children]);

  return (
    <div className="relative">
      <div
        ref={ref}
        onScroll={update}
        className={cn("v2-scroll overflow-y-auto", className)}
      >
        {children}
      </div>
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-card to-transparent transition-opacity duration-200",
          fade.top ? "opacity-100" : "opacity-0",
        )}
      />
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-card to-transparent transition-opacity duration-200",
          fade.bottom ? "opacity-100" : "opacity-0",
        )}
      />
    </div>
  );
}
