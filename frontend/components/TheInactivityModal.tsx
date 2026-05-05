import { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { login } from "@/lib/msal-auth";

export function TheInactivityModal() {
  const [show, setShow] = useState(false);
  const [signing, setSigning] = useState(false);

  useEffect(() => {
    const handler = () => setShow(true);
    window.addEventListener("inactiveUser", handler);
    return () => window.removeEventListener("inactiveUser", handler);
  }, []);

  async function handleSignIn() {
    setSigning(true);
    await login();
    setSigning(false);
    setShow(false);
  }

  if (!show) return null;

  return (
    <div className="fixed left-0 top-0 z-50 flex h-full w-full items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-[600px] rounded-sm bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg">Session Expired</h2>
        <p className="mb-10 font-thin">
          Welcome back! For your security, your session has timed out. Please
          sign in to continue.
        </p>
        <Button onClick={handleSignIn} disabled={signing}>
          {!signing ? "Sign In" : "Signing in..."}
        </Button>
      </div>
    </div>
  );
}
