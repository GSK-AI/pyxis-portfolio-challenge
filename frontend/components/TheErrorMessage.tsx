import { cn } from "@/lib/utils";
import { Button } from "./ui/button";

export const TheErrorMessage = ({
  className,
  displayMessage = "Error fetching data",
  error,
  handleRetry,
  isError,
}: {
  className?: string;
  displayMessage?: string;
  error?: string;
  handleRetry?: () => void;
  isError: boolean;
}) => {
  if (!isError) return null;
  return (
    <div
      className={cn(
        "mb-10 flex items-center justify-between rounded-xl bg-red-50 p-4 ring-1 ring-red-200",
        className,
      )}
    >
      <div>
        {displayMessage}: {error}
      </div>
      {!!handleRetry && (
        <Button onClick={handleRetry} type="button" variant={"link"}>
          Retry
        </Button>
      )}
    </div>
  );
};
