"use client";

import { useEffect, useState } from "react";
import { getHealthStatus } from "@/lib/backendCalls";
import { ConnectionSplashV2 } from "@/components/v2/SplashScreenV2";

export default function TheBackendHealth({
  children,
}: {
  children: React.ReactNode;
}) {
  const [status, setStatus] = useState<"loading" | "healthy" | "error">(
    "loading",
  );
  const checkHealth = async () => {
    setStatus("loading");
    try {
      const healthStatus = await getHealthStatus();
      healthStatus.status === "ok"
        ? setTimeout(() => setStatus("healthy"), 1000)
        : setStatus("error");
    } catch (error) {
      setStatus("error");
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  function connectionLoader() {
    return (
      <ConnectionSplashV2 status={status === "error" ? "error" : "loading"} />
    );
  }

  function loadAppView() {
    return children;
  }

  return status === "healthy" ? <>{loadAppView()}</> : connectionLoader();
}
