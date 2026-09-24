"use client";

import React, { createContext, useContext, ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { getIdToken } from "@/lib/msal-auth";
import { jwtDecode } from "jwt-decode";
import type { JwtPayload } from "@/lib/definitions";
import { TheInactivityModal } from "./TheInactivityModal";
import InactivityTracker from "@/lib/Inactivity";
import { useEffect } from "react";
import { AuthSplashV2, AuthErrorSplashV2 } from "./v2/SplashScreenV2";

const inactivity = new InactivityTracker(40);

interface AuthContextType {
  token: string | null;
  user: JwtPayload | null;
  isLoading: boolean;
  isError: boolean;
  error: any;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const {
    data: token,
    isFetching,
    isError,
    error,
  } = useQuery({
    queryKey: ["getIdToken"],
    queryFn: () => getIdToken(),
    retry: false,
  });

  // Decode the token to get user information
  const user = React.useMemo(() => {
    if (!token) return null;
    try {
      return jwtDecode<JwtPayload>(token);
    } catch (error) {
      console.error("Failed to decode token:", error);
      return null;
    }
  }, [token]);

  const isAuthenticated = !!token && !!user;

  useEffect(() => {
    if (isFetching || isError) return;
    if (isAuthenticated) {
      inactivity.initialize();
      return () => inactivity.destroy();
    }
  }, [isFetching, isError, isAuthenticated]);

  const contextValue: AuthContextType = {
    token: token || null,
    user,
    isLoading: isFetching,
    isError,
    error,
    isAuthenticated,
  };

  // Error UI
  if (isError) {
    let errorMsg = "An unknown error occurred";
    if (error instanceof Error) errorMsg = error.message;
    else if (typeof error === "string") errorMsg = error;
    else if (error && typeof error === "object" && "message" in error)
      errorMsg = (error as any).message;

    return (
      <AuthContext.Provider value={contextValue}>
        <AuthErrorSplashV2 errorMsg={errorMsg} />
      </AuthContext.Provider>
    );
  }

  // Loading UI
  if (isFetching) {
    return (
      <AuthContext.Provider value={contextValue}>
        <AuthSplashV2 />
      </AuthContext.Provider>
    );
  }

  // Authenticated: Render children with context
  return (
    <AuthContext.Provider value={contextValue}>
      {children}
      <TheInactivityModal />
    </AuthContext.Provider>
  );
};
