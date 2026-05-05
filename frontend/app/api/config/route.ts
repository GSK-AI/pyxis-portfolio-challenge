import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    clientId: process.env.NEXT_PUBLIC_AZURE_CLIENT_ID || "",
    authority: process.env.NEXT_PUBLIC_AZURE_AUTHORITY || "",
    backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL || "",
    backendGameUrl: process.env.NEXT_PUBLIC_BACKEND_URL_GAME || "",
  });
}
