"use client";

import { handleLogin } from "@/lib/msal-auth";
import { Button } from "./ui/button";
import { LogIn } from "lucide-react";

export function TheControlSignIn() {
  return (
    <Button size="sm" onClick={handleLogin}>
      <LogIn /> Sign In
    </Button>
  );
}
