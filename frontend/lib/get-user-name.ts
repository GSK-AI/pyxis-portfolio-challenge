import { getIdToken } from "./msal-auth";

export async function getUserName(): Promise<string | undefined> {
  try {
    const token = await getIdToken();
    if (!token) return undefined;

    // Safely parse JWT payload
    const parts = token.split(".");
    if (parts.length !== 3) return undefined;

    const payload = JSON.parse(atob(parts[1]));
    return payload.name || payload.email || payload.preferred_username;
  } catch (error) {
    console.error("Failed to get user name:", error);
    return undefined;
  }
}
