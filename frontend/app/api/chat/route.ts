import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "https://customer-support-bot-nehk.onrender.com";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 85000); // slightly less than frontend's 90s

    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });

  } catch (err: unknown) {
    const isTimeout = err instanceof Error && err.name === "AbortError";
    return NextResponse.json(
      {
        response: isTimeout
          ? "⏳ Server is waking up. Please try again in 30 seconds."
          : "⚠️ Failed to reach the backend.",
        escalated: false,
      },
      { status: isTimeout ? 504 : 500 }
    );
  }
}