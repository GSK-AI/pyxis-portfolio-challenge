"use client";

import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

interface HomeScreenContextValue {
  isHomeScreen: boolean;
  setIsHomeScreen: (value: boolean) => void;
}

const HomeScreenContext = createContext<HomeScreenContextValue>({
  isHomeScreen: true,
  setIsHomeScreen: () => {},
});

export function HomeScreenProvider({ children }: { children: ReactNode }) {
  const [isHomeScreen, setIsHomeScreen] = useState(true);
  return (
    <HomeScreenContext.Provider value={{ isHomeScreen, setIsHomeScreen }}>
      {children}
    </HomeScreenContext.Provider>
  );
}

export function useHomeScreen() {
  return useContext(HomeScreenContext);
}
