import "@/app/ui/global.css";
import { type Metadata } from "next";
import { TheHeader } from "@/components/TheHeader";
import { TheFooter } from "@/components/TheFooter";
import { HomeButton } from "@/components/HomeButton";
import TheBackendHealth from "@/components/TheBackendHealth";
import { AuthProvider } from "@/components/AuthContext";
import { TheQueryClientProvider } from "@/components/TheQueryClientProvider";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { CarouselTourWrapper } from "@/components/CarouselTour/CarouselTourWrapper";
import { NextStepClient } from "@/components/NextStepClient";
import { HomeScreenProvider } from "@/context/HomeScreenContext";

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
    <html lang="en">
      <body className="flex min-h-screen flex-col">
        <TheQueryClientProvider>
          <TooltipProvider>
            <AuthProvider>
              <TheBackendHealth>
                <CarouselTourWrapper>
                  <NextStepClient>
                    <HomeScreenProvider>
                    <div className="flex min-h-screen flex-col">
                      {showNavbar && <TheHeader />}
                      <HomeButton showNavbar={showNavbar} />
                      <main className="flex-1 pb-4 pt-6">{children}</main>
                      {showFooter && <TheFooter />}
                    </div>
                    </HomeScreenProvider>
                  </NextStepClient>
                </CarouselTourWrapper>
              </TheBackendHealth>
            </AuthProvider>
          </TooltipProvider>
        </TheQueryClientProvider>
        <Toaster />
      </body>
    </html>
  );
}
