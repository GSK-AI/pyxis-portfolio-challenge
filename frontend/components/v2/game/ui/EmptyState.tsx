import type { LucideIcon } from "lucide-react";

/** Quiet empty state for panels — no big grey void. */
export function EmptyState({
  icon: Icon,
  message,
  hint,
}: {
  icon?: LucideIcon;
  message: string;
  hint?: string;
}) {
  return (
    <div className="flex h-full min-h-24 flex-col items-center justify-center gap-2 rounded bg-gradient-to-b from-secondary/40 to-transparent py-6 text-center">
      {Icon && (
        <div className="flex size-9 items-center justify-center rounded-full bg-[var(--accent-soft)]">
          <Icon className="size-4 text-primary" />
        </div>
      )}
      <p className="text-sm text-muted-foreground">{message}</p>
      {hint && <p className="text-xs text-muted-foreground/60">{hint}</p>}
    </div>
  );
}
