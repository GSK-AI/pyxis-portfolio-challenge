import Link from "next/link";
import { headers } from "next/headers";
import { House } from "lucide-react";

export async function HomeButton() {
  const headersList = await headers();
  const pathname = headersList.get("x-pathname") ?? "/";

  if (pathname === "/") return null;

  return (
    <div className="border-b border-gray-100 bg-gray-50 px-4 py-2">
      <Link
        href="/"
        className="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
      >
        <House className="h-4 w-4" />
        Home
      </Link>
    </div>
  );
}
