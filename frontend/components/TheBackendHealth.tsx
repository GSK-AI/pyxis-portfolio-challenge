"use client";

import { useEffect, useState } from "react";
import { ShieldOff } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getHealthStatus } from "@/lib/backendCalls";
import { usePathname } from "next/navigation";

export default function TheBackendHealth({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const requireAuthentication = !pathname.includes("logged-out");
  const [status, setStatus] = useState<"loading" | "healthy" | "error">(
    "loading",
  );
  const [lastChecked, setLastChecked] = useState<string>("");

  const checkHealth = async () => {
    setStatus("loading");
    if (!requireAuthentication) {
      setStatus("healthy");
      return;
    }

    try {
      const healthStatus = await getHealthStatus();
      healthStatus.status === "ok"
        ? setTimeout(() => setStatus("healthy"), 1000)
        : setStatus("error");
    } catch (error) {
      setStatus("error");
    }
    setLastChecked(new Date().toLocaleString());
  };

  useEffect(() => {
    checkHealth();
  }, []);

  function errorView() {
    return (
      <Alert className="max-w-[600px] text-red-500">
        <ShieldOff className="h-4 w-4" color="red" />
        <AlertTitle>Error in Establishing Connection</AlertTitle>
        <AlertDescription>
          We apologize for the inconvenience. Please try again shortly, and if
          the issue persists, contact your application administrator for
          assistance.
        </AlertDescription>
      </Alert>
    );
  }

  function connectionLoader() {
    return (
      <div className="c-splash-screen flex h-screen w-screen items-center justify-center font-light">
        <div className="w-[900px] rounded-lg bg-white p-10">
          <img
            src="/images/gsk-logo-color.png"
            alt="GSK"
            className="max-w-[80px]"
          />
          <h1 className="my-4 mb-8 text-2xl">Welcome to Pyxis</h1>
          {status !== "error" && (
            <p className="mb-6 mt-4 font-bold">Establishing Connection...</p>
          )}

          {/* <div className="my-2 text-sm">
            {lastChecked && <div>Last Checked: {lastChecked}</div>}
          </div> */}

          <div className="mt-8">
            {status === "loading" && (
              <Skeleton className="h-[20px] w-[400px] rounded-md" />
            )}
            {status === "error" && errorView()}
          </div>
        </div>
      </div>
    );
  }

  function loadAppView() {
    return children;
  }

  return status === "healthy" ? (
    <>{loadAppView()}</>
  ) : (
    connectionLoader()
  );
}
