"use client";

import { useEffect, useState } from "react";
import { ChevronsLeftRightEllipsis, ShieldOff } from "lucide-react";
import { getHealthStatus } from "@/lib/backendCalls";

export function WidgetBackendConnection() {
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

  return (
    <div>
      {status === "loading" && <div>Connecting to Backend APIs...</div>}
      {status === "error" && (
        <div className="flex items-center gap-2 text-red-500">
          <ShieldOff size={16} />
          <div>Failed to connect</div>
        </div>
      )}
      {status === "healthy" && (
        <div className="flex items-center gap-2 text-green-500">
          <ChevronsLeftRightEllipsis size={24} /> <div>Connected</div>
        </div>
      )}
    </div>
  );
}
