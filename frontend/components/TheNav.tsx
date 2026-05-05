"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CarouselTourDialog } from "./CarouselTour/CarouselTourDialog";
import { StartOnboardingTour } from "./InvestmentGame/StartOnboardingTour";

type NavLink = {
  name: string;
  href: string;
  disabled?: boolean;
};

const gameLinks: NavLink[] = [
  { name: "Portfolio Challenge", href: "/" },
  { name: "Resources", href: "/resources" },
];

export default function NavTabs() {
  const pathname = usePathname();
  let navRender = gameLinks; // Default to game links since investment game is now root

  return (
    <div className="flex items-center">
      {navRender.map((link) => {
        const isActive = link.href === pathname;

        if (link.disabled) {
          return (
            <div
              key={link.name}
              className="cursor-not-allowed px-4 py-4 font-thin text-gray-400"
              title="Coming soon"
            >
              {link.name}
            </div>
          );
        }

        return (
          <Link href={link.href} key={link.name}>
            <div
              className={`px-4 py-4 font-thin transition-all hover:bg-gray-100 ${
                isActive ? "border-b-4 border-[#1CA8C0]" : ""
              }`}
            >
              {link.name}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
