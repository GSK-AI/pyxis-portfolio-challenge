"use client";

import { usePathname } from "next/navigation";
import LayoutContainer from "./LayoutContainer";
import { WidgetBackendConnection } from "./WidgetBackendConnection";

export function TheFooter() {
  const pathname = usePathname();
  const requireAuthentication = !pathname.includes("logged-out");

  return (
    <footer>
      <LayoutContainer>
        <div className="flex items-center justify-between border-t border-gray-100 p-4 text-sm text-gray-400">
          <div>Developed by AIML, 2025</div>
          {requireAuthentication && <WidgetBackendConnection />}
        </div>
      </LayoutContainer>
    </footer>
  );
}
