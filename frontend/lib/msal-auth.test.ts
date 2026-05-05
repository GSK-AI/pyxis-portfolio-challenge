// File: useMsalAuth.test.ts

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import * as msal from "@azure/msal-browser";
import { getIdToken, logout } from "./msal-auth";
import { jwtDecode } from "jwt-decode";

vi.mock("@azure/msal-browser");
vi.mock("jwt-decode");
vi.stubGlobal("fetch", vi.fn());

const DUMMY_CONFIG = { clientId: "CLIENT_ID", authority: "AUTHORITY" };
const DUMMY_ID_TOKEN = "DUMMY_ID_TOKEN";
const DUMMY_EXP = Math.floor(Date.now() / 1000) + 3600; // 1 hour from now

const createFakeMsalInstance = () => ({
  initialize: vi.fn().mockResolvedValue(undefined),
  handleRedirectPromise: vi.fn().mockResolvedValue(undefined),
  getAllAccounts: vi.fn().mockReturnValue([{ homeAccountId: "1" }]),
  setActiveAccount: vi.fn(),
  acquireTokenSilent: vi.fn().mockResolvedValue({ idToken: DUMMY_ID_TOKEN }),
  loginRedirect: vi.fn().mockResolvedValue(undefined),
  getConfiguration: vi.fn().mockReturnValue({ auth: DUMMY_CONFIG }),
  logoutRedirect: vi.fn().mockResolvedValue(undefined),
});

describe("useMsalAuth", () => {
  let originalMsalInstance: any;

  beforeEach(() => {
    // Reset module state
    vi.resetModules();

    // Mock fetch for config endpoint
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => DUMMY_CONFIG,
    });

    // Mock jwtDecode
    (jwtDecode as any).mockImplementation(() => ({ exp: DUMMY_EXP }));

    // Save and mock msal.PublicClientApplication
    originalMsalInstance = (msal as any).PublicClientApplication;
    (msal as any).PublicClientApplication = vi.fn(() =>
      createFakeMsalInstance(),
    );
  });

  afterEach(() => {
    // Restore msal.PublicClientApplication
    (msal as any).PublicClientApplication = originalMsalInstance;
    vi.clearAllMocks();
  });

  it("fetches ID token for a logged-in user", async () => {
    const idToken = await getIdToken();
    expect(idToken).toBe(DUMMY_ID_TOKEN);
  });

  it("initiates loginRedirect when no accounts", async () => {
    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.getAllAccounts = vi.fn().mockReturnValue([]);
    fakeMsalInstance.loginRedirect = vi.fn().mockResolvedValue(undefined);

    // Rewire the msal instance factory to use our custom instance
    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    // Clear cached config/instance (if running multiple tests)
    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    expect(fakeMsalInstance.loginRedirect).toHaveBeenCalledWith({
      scopes: [`${DUMMY_CONFIG.clientId}/.default`],
      redirectUri: window.location.origin,
    });
  });

  it("calls acquireTokenSilent and caches the token", async () => {
    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.acquireTokenSilent = vi
      .fn()
      .mockResolvedValue({ idToken: DUMMY_ID_TOKEN });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    // First call populates cache
    const token1 = await getIdToken();
    expect(token1).toBe(DUMMY_ID_TOKEN);
    // jwtDecode called once
    expect(jwtDecode).toHaveBeenCalledWith(DUMMY_ID_TOKEN);

    // Second call should use cache (acquireTokenSilent not called again)
    fakeMsalInstance.acquireTokenSilent.mockClear();
    const token2 = await getIdToken();
    expect(token2).toBe(DUMMY_ID_TOKEN);
    expect(fakeMsalInstance.acquireTokenSilent).not.toHaveBeenCalled();
  });

  it("falls back to loginRedirect on acquireTokenSilent failure", async () => {
    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.acquireTokenSilent = vi
      .fn()
      .mockRejectedValue(new Error("No token"));
    fakeMsalInstance.loginRedirect = vi.fn().mockResolvedValue(undefined);

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    expect(fakeMsalInstance.loginRedirect).toHaveBeenCalledWith({
      scopes: [`${DUMMY_CONFIG.clientId}/.default`],
      redirectUri: window.location.origin,
    });
  });

  it("logs out via logoutRedirect", async () => {
    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.logoutRedirect = vi.fn().mockResolvedValue(undefined);

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { logout: freshLogout } = await import("./msal-auth");
    await freshLogout();

    expect(fakeMsalInstance.logoutRedirect).toHaveBeenCalled();
  });

  it("throws if config fetch fails", async () => {
    (fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Server error",
    });

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");

    await expect(freshGetIdToken()).rejects.toThrow("Failed to fetch config");
  });

  it("returns local-dev-token if config missing clientId/authority", async () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");

    const token = await freshGetIdToken();
    expect(token).toBe("local-dev-token");
  });

  it("returns testing token when pyxis-testing-token exists in localStorage", async () => {
    const testToken = "test-token-from-localstorage";

    // Mock localStorage
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockImplementation((key) => {
          if (key === "pyxis-testing-token") return testToken;
          return null;
        }),
      },
      writable: true,
    });

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    const result = await freshGetIdToken();

    expect(result).toBe(testToken);
    expect(window.localStorage.getItem).toHaveBeenCalledWith(
      "pyxis-testing-token",
    );
  });

  it("treats expired token as invalid and fetches new token", async () => {
    // Mock expired token
    (jwtDecode as any).mockImplementation(() => ({
      exp: Math.floor(Date.now() / 1000) - 100, // Expired 100 seconds ago
    }));

    // Mock localStorage to return null (no testing token)
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
      },
      writable: true,
    });

    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.acquireTokenSilent = vi
      .fn()
      .mockResolvedValue({ idToken: DUMMY_ID_TOKEN });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    // Should call acquireTokenSilent because cached token is expired
    expect(fakeMsalInstance.acquireTokenSilent).toHaveBeenCalled();
  });

  it("handles jwtDecode error and treats token as expired", async () => {
    // Mock jwtDecode to throw an error
    (jwtDecode as any).mockImplementation(() => {
      throw new Error("Invalid token");
    });

    // Mock localStorage to return null
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
      },
      writable: true,
    });

    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.acquireTokenSilent = vi
      .fn()
      .mockResolvedValue({ idToken: DUMMY_ID_TOKEN });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    // Should call acquireTokenSilent because token decode failed
    expect(fakeMsalInstance.acquireTokenSilent).toHaveBeenCalled();
  });

  it("calls login function directly", async () => {
    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.loginRedirect = vi.fn().mockResolvedValue(undefined);

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { login } = await import("./msal-auth");
    await login();

    expect(fakeMsalInstance.loginRedirect).toHaveBeenCalledWith({
      scopes: [`${DUMMY_CONFIG.clientId}/.default`],
      redirectUri: window.location.origin,
    });
  });

  it("handles login with error in handleLogin", async () => {
    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.loginRedirect = vi
      .fn()
      .mockRejectedValue(new Error("Login failed"));

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    // Mock location object
    const mockLocation = {
      ...window.location,
      href: "",
      origin: window.location.origin,
    };

    // Store original location
    const originalLocation = window.location;

    // Replace window.location
    delete (window as any).location;
    (window as any).location = mockLocation;

    const { handleLogin } = await import("./msal-auth");
    await handleLogin();

    expect(mockLocation.href).toBe(window.location.origin);

    // Restore location
    (window as any).location = originalLocation;
  });

  it("handles redirect promise with account response", async () => {
    const testAccount = { homeAccountId: "test-account" };
    const testIdToken = "test-redirect-token";

    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.handleRedirectPromise = vi.fn().mockResolvedValue({
      account: testAccount,
      idToken: testIdToken,
    });
    fakeMsalInstance.setActiveAccount = vi.fn();

    // Mock localStorage to return null
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
      },
      writable: true,
    });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    expect(fakeMsalInstance.handleRedirectPromise).toHaveBeenCalled();
    expect(fakeMsalInstance.setActiveAccount).toHaveBeenCalledWith(testAccount);
  });

  it("handles redirect promise error silently", async () => {
    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.handleRedirectPromise = vi
      .fn()
      .mockRejectedValue(new Error("Redirect error"));
    fakeMsalInstance.getAllAccounts = vi.fn().mockReturnValue([]);
    fakeMsalInstance.loginRedirect = vi.fn().mockResolvedValue(undefined);

    // Mock localStorage to return null
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
      },
      writable: true,
    });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");

    // Should not throw error, should handle silently
    await expect(freshGetIdToken()).resolves.toBeUndefined();
    expect(fakeMsalInstance.handleRedirectPromise).toHaveBeenCalled();
  });

  it("handles config loading failure", async () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => null, // Simulate null config response
    });

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");

    await expect(freshGetIdToken()).rejects.toThrow(
      "Failed to load configuration",
    );
  });

  it("handles token with missing exp claim", async () => {
    // Mock jwtDecode to return token without exp
    (jwtDecode as any).mockImplementation(() => ({})); // No exp property

    // Mock localStorage to return null (testing token)
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
      },
      writable: true,
    });

    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.acquireTokenSilent = vi
      .fn()
      .mockResolvedValue({ idToken: DUMMY_ID_TOKEN });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    // Should call acquireTokenSilent because token has no exp claim (treated as expired)
    expect(fakeMsalInstance.acquireTokenSilent).toHaveBeenCalled();
  });

  it("handles token with exp as null/undefined", async () => {
    // Mock jwtDecode to return token with null exp
    (jwtDecode as any).mockImplementation(() => ({ exp: null }));

    // Mock localStorage to return null (testing token)
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
      },
      writable: true,
    });

    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.acquireTokenSilent = vi
      .fn()
      .mockResolvedValue({ idToken: DUMMY_ID_TOKEN });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    // Should call acquireTokenSilent because token exp is null (treated as expired)
    expect(fakeMsalInstance.acquireTokenSilent).toHaveBeenCalled();
  });

  it("handles token with exp as 0 (falsy value)", async () => {
    // Mock jwtDecode to return token with exp: 0 (falsy)
    (jwtDecode as any).mockImplementation(() => ({ exp: 0 }));

    // Mock localStorage to return null (testing token)
    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: vi.fn().mockReturnValue(null),
      },
      writable: true,
    });

    const fakeMsalInstance = createFakeMsalInstance();
    fakeMsalInstance.acquireTokenSilent = vi
      .fn()
      .mockResolvedValue({ idToken: DUMMY_ID_TOKEN });

    (msal as any).PublicClientApplication = vi.fn(() => fakeMsalInstance);

    const { getIdToken: freshGetIdToken } = await import("./msal-auth");
    await freshGetIdToken();

    // Should call acquireTokenSilent because token exp is 0 (treated as expired)
    expect(fakeMsalInstance.acquireTokenSilent).toHaveBeenCalled();
  });

  // Note: Server-side rendering test removed as it's not practical to test in jsdom environment
  // Line 74 handles the case where window is undefined, but this would require Node.js environment testing
  // which is beyond the scope of unit tests that rely on browser APIs like MSAL
});
