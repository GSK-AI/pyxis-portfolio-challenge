"use client";

import { Button } from "@/components/ui/button";
import { handleLogin } from "@/lib/msal-auth";
import { LogIn } from "lucide-react";

export default function LoggedOut() {
  return (
    <div className="c-splash-screen container mx-auto flex min-h-[80vh] items-center justify-center">
      <div className="min-w-[900px]">
        <h1 className="mb-2 text-2xl">You've been logged out</h1>
        <p>We appreciate your time and hope to see you again soon.</p>

        <div className="mt-10 flex flex-col gap-2">
          <small>Want to log back in?</small>
          <div>
            <Button size="sm" variant="secondary" onClick={handleLogin}>
              <LogIn /> Sign In
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
