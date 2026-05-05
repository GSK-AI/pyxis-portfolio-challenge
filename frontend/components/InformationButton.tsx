import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { Info } from "lucide-react";

type InformationButtonProps = {
  className?: string;
  description: string;
  title: string;
  buttonClassName?: string;
};

export function InformationButton({
  className,
  description,
  title,
  buttonClassName = "h-5 w-5",
}: InformationButtonProps) {
  return (
    <Popover>
      <PopoverTrigger
        className={cn(
          "w-auto rounded-full p-1 opacity-70 hover:bg-accent hover:text-accent-foreground",
          className,
        )}
      >
        <Info className={buttonClassName} />
      </PopoverTrigger>
      <PopoverContent className="w-80" side="top">
        <div className="grid gap-4">
          <div className="space-y-2">
            <h4 className="font-medium leading-none">{title}</h4>
            <p className="text-md whitespace-pre-wrap text-muted-foreground">
              {description}
            </p>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
