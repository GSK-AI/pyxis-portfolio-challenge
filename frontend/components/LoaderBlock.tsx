import { Skeleton } from "@/components/ui/skeleton";

export function LoaderBlock() {
  return (
    <div className="flex flex-col space-y-3 p-6">
      <Skeleton className="h-6 w-[500px] bg-white/50" />
      <Skeleton className="h-6 w-[400px] bg-white/40" />
      <Skeleton className="h-[100px] w-[200px] bg-white/50" />
    </div>
  );
}
