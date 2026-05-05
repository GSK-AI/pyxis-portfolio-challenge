"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { type ReactNode } from "react";

const queryClient = new QueryClient();

type TheQueryClientProviderProps = {
  children: ReactNode;
};

export const TheQueryClientProvider = ({
  children,
}: TheQueryClientProviderProps) => {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};
