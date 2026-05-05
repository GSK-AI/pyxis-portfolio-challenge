import * as msal from "@azure/msal-browser";
import { jwtDecode } from "jwt-decode";
import type { JwtPayload } from "@/lib/definitions";

let msalInstance: msal.PublicClientApplication | null = null;
let isMsalInitialized = false;
let idTokenCache: string | null = null;
let cachedConfig: { clientId: string; authority: string } | null = null;

async function getConfig() {
  if (cachedConfig) return cachedConfig;
  const response = await fetch("/api/config");
  if (!response.ok) throw new Error("Failed to fetch config");
  cachedConfig = await response.json();

  if (!cachedConfig) {
    throw new Error("Failed to load configuration");
  }
  // Allow empty config for local development without Azure AD
  return cachedConfig;
}

function isAuthConfigured(): boolean {
  return !!(cachedConfig?.clientId && cachedConfig?.authority);
}

async function getMsalInstance() {
  if (msalInstance && isMsalInitialized) return msalInstance;
  const config = await getConfig();

  // Don't initialize MSAL if auth is not configured
  if (!config.clientId || !config.authority) {
    throw new Error("MSAL not available - Azure AD not configured");
  }

  if (!msalInstance) {
    msalInstance = new msal.PublicClientApplication({
      auth: {
        clientId: config.clientId,
        authority: config.authority,
        redirectUri: window.location.origin,
      },
      cache: { cacheLocation: "localStorage" },
    });
  }
  if (!isMsalInitialized) {
    await msalInstance.initialize();
    isMsalInitialized = true;
  }
  return msalInstance;
}

function isTokenExpired(token: string): boolean {
  try {
    const { exp } = jwtDecode<JwtPayload>(token);
    return !exp || Date.now() > exp * 1000 - 60 * 1000;
  } catch {
    return true;
  }
}

async function handleRedirectIfNeeded() {
  const msalInstance = await getMsalInstance();
  try {
    const resp = await msalInstance.handleRedirectPromise();
    if (resp && resp.account) {
      msalInstance.setActiveAccount(resp.account);
      idTokenCache = resp.idToken;
    }
  } catch (e) {
    // Silently ignore
  }
}

export async function getIdToken(): Promise<string | undefined> {
  // Check for testing token in localStorage (for local development)
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem("pyxis-testing-token")
      : undefined;
  if (token) return token;

  // Load config to check if auth is configured
  await getConfig();

  // If Azure AD auth is not configured, return a dev token for local development
  if (!isAuthConfigured()) {
    console.log("[LOG]: Azure AD not configured, using local development mode");
    return "local-dev-token";
  }

  await handleRedirectIfNeeded();
  const msalInstance = await getMsalInstance();
  const accounts = msalInstance.getAllAccounts();

  if (idTokenCache && !isTokenExpired(idTokenCache)) {
    console.log("[LOG]: Returning cached, valid session");
    return idTokenCache;
  }

  if (accounts.length === 0) {
    await msalInstance.loginRedirect({
      scopes: [`${msalInstance.getConfiguration().auth.clientId}/.default`],
      redirectUri: window.location.origin,
    });
    return undefined;
  }

  msalInstance.setActiveAccount(accounts[0]);
  try {
    const tokenResponse = await msalInstance.acquireTokenSilent({
      account: accounts[0],
      scopes: [`${msalInstance.getConfiguration().auth.clientId}/.default`],
      forceRefresh: true,
    });
    idTokenCache = tokenResponse.idToken;
    console.log("[LOG]: Signing in user...");
    return idTokenCache;
  } catch (err) {
    console.log("[LOG]: Signing in failed, redirecting user...");
    await msalInstance.loginRedirect({
      scopes: [`${msalInstance.getConfiguration().auth.clientId}/.default`],
      redirectUri: window.location.origin,
    });
    return undefined;
  }
}

export async function logout() {
  idTokenCache = null;
  await getConfig();
  if (!isAuthConfigured()) {
    console.log("[LOG]: Logout skipped - Azure AD not configured");
    window.location.href = window.location.origin + "/logged-out";
    return;
  }
  const msalInstance = await getMsalInstance();
  await msalInstance.logoutRedirect({
    postLogoutRedirectUri: window.location.origin + "/logged-out",
  });
}

export async function login() {
  await getConfig();
  if (!isAuthConfigured()) {
    console.log(
      "[LOG]: Login skipped - Azure AD not configured, using local dev mode",
    );
    return;
  }
  const msalInstance = await getMsalInstance();
  await msalInstance.loginRedirect({
    scopes: [`${msalInstance.getConfiguration().auth.clientId}/.default`],
    redirectUri: window.location.origin,
  });
}

export async function handleLogin() {
  try {
    await login();
  } catch (err) {
    location.href = window.location.origin;
  }
}
