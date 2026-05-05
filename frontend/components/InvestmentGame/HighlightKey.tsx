"use client";

export default function HighlightKey({
  showBdAcquisition = true,
}: {
  showBdAcquisition?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-5 text-xs text-gray-600">
      <div className="flex items-center gap-2">
        <span className="inline-block h-4 w-4 rounded-sm bg-amber-100 shadow-[inset_3px_0_0_0_#f59e0b]" />
        <span>New / Changed</span>
      </div>
      {showBdAcquisition && (
        <div className="flex items-center gap-2">
          <span className="inline-block h-4 w-4 rounded-sm bg-blue-100 shadow-[inset_3px_0_0_0_#3b82f6]" />
          <span>BD Acquisition</span>
        </div>
      )}
    </div>
  );
}
