"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { House } from "lucide-react";

export function HomeButton() {
  const pathname = usePathname();

  if (pathname === "/") return null;

  return (
    <div className="px-4 pt-4">
      <Link
        href="/"
        className="inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium shadow-md hover:bg-gray-50"
      >
        <House className="h-4 w-4" />
        Home
      </Link>
    </div>
  );
}
