import { Skeleton } from "@/components/ui/skeleton";

export function LoaderList() {
  return (
    <div className="flex flex-col space-y-3">
      <Skeleton className="h-6 w-[500px]" />
      <Skeleton className="h-6 w-[400px]" />
      <Skeleton className="h-2 w-[200px]" />
    </div>
  );
}
