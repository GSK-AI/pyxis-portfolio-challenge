// Backend API calls for health checking and other general endpoints
import { getIdToken } from "./msal-auth";

let cachedBackendUrl: string | null = null;

async function getBackendUrl(): Promise<string> {
  if (cachedBackendUrl) return cachedBackendUrl;

  const response = await fetch("/api/config");
  if (!response.ok) throw new Error("Failed to fetch config");
  const config = await response.json();
  cachedBackendUrl = config.backendUrl;

  if (!cachedBackendUrl) {
    throw new Error("Backend URL not configured");
  }

  return cachedBackendUrl;
}

export async function getHealthStatus(): Promise<{ status: string }> {
  try {
    const baseUrl = await getBackendUrl();
    const token = await getIdToken();

    if (!token) {
      return { status: "unauthenticated" };
    }

    const response = await fetch(`${baseUrl}/health`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      return { status: "unhealthy" };
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Health check failed:", error);
    return { status: "error" };
  }
}
