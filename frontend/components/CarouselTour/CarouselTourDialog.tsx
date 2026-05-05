import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  FullScreenDialogContent,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useCarouselTour } from "./CarouselTourContext";
import { CarouselTourContent } from "./CarouselTourContent";
import { Close } from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Checkbox } from "../ui/checkbox";
import { Label } from "../ui/label";

const showTrigger = false;

export const CarouselTourDialog = () => {
  const { isOpen, setIsOpen, doNotShowAgain, setDoNotShowAgain } =
    useCarouselTour();
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {showTrigger && (
        <DialogTrigger asChild>
          <Button variant="outline">Start Tour</Button>
        </DialogTrigger>
      )}
      <FullScreenDialogContent
        autoFocus={false}
        className="flex flex-col"
        onInteractOutside={(e) => e.preventDefault()}
        onOpenAutoFocus={(e) => {
          e.preventDefault();
        }}
      >
        <DialogHeader className="hidden">
          <DialogTitle>Pyxis Tour</DialogTitle>
          <DialogDescription>
            This is a carousel tour of the Pyxis application.
          </DialogDescription>
        </DialogHeader>
        <div className="flex w-full items-center justify-between px-8">
          <div className="flex items-center space-x-2 px-4">
            <Checkbox
              id="do-not-show-again"
              checked={doNotShowAgain}
              onCheckedChange={(newVal) => {
                setDoNotShowAgain(!!newVal);
              }}
            />
            <Label htmlFor="do-not-show-again">Do not show again</Label>
          </div>
          <Close
            asChild
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <Button
              variant={"ghost"}
              type="button"
              className="flex items-center"
            >
              <X className="h-4 w-4" />
              <span>Close</span>
            </Button>
          </Close>
        </div>
        <CarouselTourContent />
      </FullScreenDialogContent>
    </Dialog>
  );
};
