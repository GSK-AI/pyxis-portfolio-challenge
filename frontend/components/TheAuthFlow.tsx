"use client";

import { getIdToken } from "@/lib/msal-auth";
import { Skeleton } from "./ui/skeleton";
import { useQuery } from "@tanstack/react-query";
import { ReactNode, useEffect } from "react";
import { TheInactivityModal } from "./TheInactivityModal";
import InactivityTracker from "@/lib/Inactivity";
import { usePathname } from "next/navigation";

const inactivity = new InactivityTracker(40);

export const TheAuthFlow = ({ children }: { children: ReactNode }) => {
  const pathname = usePathname();
  const requireAuthentication = !pathname.includes("logged-out");

  const { isFetching, isError, error } = useQuery({
    queryKey: ["getIdToken"],
    queryFn: () => getIdToken(),
    retry: false,
    enabled: requireAuthentication,
  });

  useEffect(() => {
    if (isFetching || isError) return;
    inactivity.initialize();
    return () => inactivity.destroy();
  }, [isFetching, isError]);

  if (!requireAuthentication) {
    return <>{children}</>;
  }

  // Error UI
  if (isError) {
    let errorMsg = "An unknown error occurred";
    if (error instanceof Error) errorMsg = error.message;
    else if (typeof error === "string") errorMsg = error;
    else if (error && typeof error === "object" && "message" in error)
      errorMsg = (error as any).message;

    return (
      <div className="flex h-screen w-screen items-center justify-center font-light">
        <div className="min-w-[900px] rounded-lg bg-white p-10">
          <h1 className="my-4 text-2xl">Authentication Error</h1>
          <div>{errorMsg}</div>
        </div>
      </div>
    );
  }

  // Loading UI
  if (isFetching) {
    return (
      <div className="c-splash-screen flex h-screen w-screen items-center justify-center font-light">
        <div className="min-w-[900px] rounded-lg bg-white p-10">
          <h1 className="my-4 text-2xl">Welcome to Pyxis</h1>
          <div>Authenticating...</div>
          <div className="mt-8">
            <Skeleton className="h-[20px] w-[400px] rounded-md" />
          </div>
        </div>
      </div>
    );
  }

  // Authenticated: Render children
  return (
    <>
      {children}
      <TheInactivityModal />
    </>
  );
};
