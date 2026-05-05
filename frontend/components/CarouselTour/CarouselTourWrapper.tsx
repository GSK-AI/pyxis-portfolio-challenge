import { promises } from "fs";
import path from "path";
import { type ComponentProps, type ReactNode } from "react";
import { CarouselTourProvider } from "./CarouselTourContext";

type CarouselTourWrapperProps = {
  children: ReactNode;
};

export const CarouselTourWrapper = async ({
  children,
}: CarouselTourWrapperProps) => {
  const imagesDirectory = path.join(process.cwd(), "public", "tour-images");
  const images = await promises.readdir(imagesDirectory);
  const parsedImages: ComponentProps<typeof CarouselTourProvider>["steps"] =
    images
      .filter((image) => image.endsWith(".png"))
      .map((image) => {
        const [index, name] = image.split("_");
        return {
          index: parseInt(index),
          title: name.replace(".png", "").replace(/-/g, " "),
          imagePath: `/tour-images/${image}`,
        };
      });
  return (
    <CarouselTourProvider steps={parsedImages}>{children}</CarouselTourProvider>
  );
};
