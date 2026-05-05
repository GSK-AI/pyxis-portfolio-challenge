import Image from "next/image";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";
import { useEffect } from "react";
import { useCarouselTour } from "./CarouselTourContext";
import { useParentSize } from "@visx/responsive";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";
import { Button } from "../ui/button";
import { ArrowRight } from "lucide-react";

export const CarouselTourContent = () => {
  const { api, setApi, currentStep, setCurrentStep, steps } = useCarouselTour();
  const { parentRef, width, height } = useParentSize();

  useEffect(() => {
    if (!api) {
      return;
    }

    setCurrentStep(api.selectedScrollSnap() + 1);

    api.on("select", () => {
      setCurrentStep(api.selectedScrollSnap() + 1);
    });
  }, [api]);

  const count = steps.length;

  return (
    <>
      <div className="flex min-h-0 flex-grow flex-col">
        <Carousel
          setApi={setApi}
          orientation="horizontal"
          className="h-full w-full"
          opts={{
            startIndex: currentStep - 1,
          }}
        >
          <CarouselContent
            className="h-full w-full"
            rootClassName="h-full w-full "
            ref={parentRef}
          >
            {steps.map(({ imagePath }, index) => (
              <CarouselItem key={index}>
                <div
                  className="relative"
                  style={{
                    height,
                    width,
                  }}
                >
                  <Image
                    src={imagePath}
                    alt={`Step ${index + 1}`}
                    fill
                    style={{
                      objectFit: "contain",
                    }}
                  />
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      </div>
      <div className="flex items-center gap-2 pt-2">
        <div className="flex gap-1">
          {steps.map(({ title }, index) => (
            <Tooltip delayDuration={0} key={title}>
              <TooltipTrigger>
                <div
                  className={`h-4 w-4 cursor-pointer rounded-full bg-gray-200 ${
                    index <= currentStep - 1 ? "bg-highlight" : ""
                  } ${index < currentStep - 1 ? "opacity-50" : ""}`}
                  style={{
                    flexGrow: 1,
                  }}
                  onClick={() => {
                    api?.scrollTo(index);
                    setCurrentStep(index + 1);
                  }}
                />
              </TooltipTrigger>
              <TooltipContent>
                <div className="text-center text-sm font-medium">{title}</div>
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
        <div className="py-2 text-center text-sm text-muted-foreground">
          Slide {currentStep} of {count}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button
            type="button"
            className="text-highlight"
            variant="ghost"
            disabled={currentStep >= count}
            onClick={() => api?.scrollTo(currentStep)}
          >
            Next <ArrowRight className="text-highlight" />
          </Button>
        </div>
      </div>
    </>
  );
};
