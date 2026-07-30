import { Monitor } from "lucide-react";

export function DesktopGate({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* Shown only on narrow viewports */}
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center md:hidden">
        <Monitor className="h-12 w-12 text-gray-400" />
        <h1 className="text-xl font-semibold text-gray-800">
          Please use a desktop browser
        </h1>
        <p className="max-w-xs text-sm text-gray-500">
          Pyxis is designed for larger screens. Open this page on a desktop or
          laptop for the best experience.
        </p>
      </div>

      {/* Hidden on narrow viewports, shown on md+ */}
      <div className="hidden md:contents">{children}</div>
    </>
  );
}
