"use client";

import LayoutContainer from "./LayoutContainer";
import { usePathname } from "next/navigation";
import { TheControlSignIn } from "./TheControlSignIn";

export function TheHeader() {
  const pathname = usePathname();
  const requireAuthentication = !pathname.includes("logged-out");

  return (
    <header className="border-b-2 border-gray-100 bg-gray-50 px-4 text-black shadow">
      <LayoutContainer
        maxWidth="1920px"
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-4 py-4">
          <a href="/" className="flex items-center gap-4">
            <img
              src="/images/gsk-logo-color.png"
              alt="GSK"
              className="max-w-[80px]"
            />
            <div className="text-lg">
              Pyxis <small>v1.0.0</small>
            </div>
          </a>
        </div>

        {!requireAuthentication && <TheControlSignIn />}
      </LayoutContainer>
    </header>
  );
}
