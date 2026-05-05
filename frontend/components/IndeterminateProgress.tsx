import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "@/lib/utils";

type InfiniteProgressProps = {
  className?: string;
};

export const IndeterminateProgress = ({ className }: InfiniteProgressProps) => {
  return (
    <ProgressPrimitive.Root
      className={cn(
        "relative h-1 w-full overflow-hidden rounded-full bg-highlight-muted",
        className,
      )}
    >
      <ProgressPrimitive.Indicator
        className={cn(
          "h-full w-full flex-1 bg-highlight transition-all",
          "origin-left animate-progress",
        )}
      />
    </ProgressPrimitive.Root>
  );
};
