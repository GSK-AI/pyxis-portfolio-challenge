interface TimelineProps {
  currentTime: number;
  totalTime: number;
}

export default function Timeline({ currentTime, totalTime }: TimelineProps) {
  // Calculate progress percentage
  const progressPercentage = (currentTime / totalTime) * 100;

  return (
    <div className="flex w-full items-center gap-3">
      {/* Progress bar */}
      <div className="flex-1">
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-300">
          <div
            className="h-full bg-teal-600 transition-all duration-300 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Compact progress text */}
      <div className="flex-shrink-0 text-sm text-gray-600">
        {currentTime}/{totalTime}
      </div>
    </div>
  );
}
