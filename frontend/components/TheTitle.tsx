"use client";

export default function TheTitle({ children }: { children: React.ReactNode }) {
  return <h1 className="mb-4 text-3xl capitalize">{children}</h1>;
}
