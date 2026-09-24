import "@/app/ui/global.css";
import "@/app/ui/theme-v2.css";
import { type Metadata } from "next";
import { TheHeader } from "@/components/TheHeader";
import { TheFooter } from "@/components/TheFooter";
import TheBackendHealth from "@/components/TheBackendHealth";
import { AuthProvider } from "@/components/AuthContext";
import { TheQueryClientProvider } from "@/components/TheQueryClientProvider";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { NextStepClient } from "@/components/NextStepClient";
import { DesktopGate } from "@/components/DesktopGate";

export const metadata: Metadata = {
  title: "Pyxis | GSK",
  description: "Pyxis | GSK",
  icons: {
    icon: [
      {
        url: "/favicon.png",
        href: "/favicon.png",
        type: "image/png",
      },
    ],
  },
};

const showNavbar = process.env.NEXT_PUBLIC_SHOW_NAVBAR === "true";
const showFooter = process.env.NEXT_PUBLIC_SHOW_FOOTER === "true";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="ui-v2">
      <body className="flex flex-col">
        <DesktopGate>
          <TheQueryClientProvider>
            <TooltipProvider>
              <AuthProvider>
                <TheBackendHealth>
                  <NextStepClient>
                    <div
                      id="main-scroll-container"
                      className="flex flex-col overflow-x-hidden"
                    >
                      {showNavbar && <TheHeader />}
                      <main className="min-w-0 flex-1 pb-4 pt-6">
                        {children}
                      </main>
                      {showFooter && <TheFooter />}
                    </div>
                  </NextStepClient>
                </TheBackendHealth>
              </AuthProvider>
            </TooltipProvider>
          </TheQueryClientProvider>
          <Toaster />
        </DesktopGate>
      </body>
    </html>
  );
}
