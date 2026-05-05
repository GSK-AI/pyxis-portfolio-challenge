"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { type CarouselApi } from "../ui/carousel";

type CarouselStep = {
  index: number;
  title: string;
  imagePath: string;
};

type CarouselTourContextType = {
  steps: CarouselStep[];
  api: CarouselApi;
  setApi: (api: CarouselApi) => void;
  currentStep: number;
  setCurrentStep: (step: number) => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  doNotShowAgain: boolean;
  setDoNotShowAgain: (val: boolean) => void;
};

const CarouselTourContext = createContext<CarouselTourContextType | undefined>(
  undefined,
);

const LOCAL_STORAGE_KEY_DO_NOT_SHOW_AGAIN = "do-not-show-again";

export const CarouselTourProvider = ({
  children,
  steps,
}: {
  children: React.ReactNode;
  steps: CarouselStep[];
}) => {
  const [api, setApi] = useState<CarouselApi>();
  const [currentStep, setCurrentStep] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [doNotShowAgain, setDoNotShowAgain] = useState(false);

  useEffect(() => {
    const isClient = typeof window !== "undefined";
    if (isClient) {
      const doNotShowAgain = localStorage.getItem(
        LOCAL_STORAGE_KEY_DO_NOT_SHOW_AGAIN,
      );
      if (doNotShowAgain) {
        setDoNotShowAgain(true);
        setIsOpen(false);
      } else {
        setDoNotShowAgain(false);
        setIsOpen(true);
      }
    }
  }, []);

  const setDONotShowAgainWithLocalStorage = useCallback((val: boolean) => {
    setDoNotShowAgain(val);
    if (val) {
      localStorage.setItem(LOCAL_STORAGE_KEY_DO_NOT_SHOW_AGAIN, "true");
    } else {
      localStorage.removeItem(LOCAL_STORAGE_KEY_DO_NOT_SHOW_AGAIN);
    }
  }, []);

  return (
    <CarouselTourContext.Provider
      value={{
        api,
        setApi,
        currentStep,
        setCurrentStep,
        isOpen,
        setIsOpen,
        steps,
        doNotShowAgain,
        setDoNotShowAgain: setDONotShowAgainWithLocalStorage,
      }}
    >
      {children}
    </CarouselTourContext.Provider>
  );
};

export const useCarouselTour = () => {
  const context = useContext(CarouselTourContext);
  if (!context) {
    throw new Error(
      "useCarouselTour must be used within a CarouselTourProvider",
    );
  }
  return context;
};
