import { createHmac, timingSafeEqual } from "crypto";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE_NAME = "gd_session";
const MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

// UX redirect only - not the security boundary. Under Vercel Services
// routing, /api/* requests never reach this frontend service at all, so
// this proxy cannot enforce anything for the API; the actual enforcement
// is the require_auth dependency in server/_auth.py on every tool route.
function isValidSession(cookieValue: string | undefined): boolean {
  if (!cookieValue) return false;
  const secret = process.env.SESSION_SECRET;
  if (!secret) return false;

  const [issuedAt, signature] = cookieValue.split(".");
  if (!issuedAt || !signature || !/^\d+$/.test(issuedAt)) return false;

  const expected = createHmac("sha256", secret).update(issuedAt).digest("hex");
  const expectedBuf = Buffer.from(expected, "utf8");
  const actualBuf = Buffer.from(signature, "utf8");
  if (expectedBuf.length !== actualBuf.length) return false;
  if (!timingSafeEqual(expectedBuf, actualBuf)) return false;

  const age = Date.now() / 1000 - Number(issuedAt);
  return age >= 0 && age <= MAX_AGE_SECONDS;
}

// The Next.js matcher's negative-lookahead idiom did not reliably exclude
// these paths under this version's dev server (confirmed empirically: static
// JS chunk requests were being redirected to /login, which returns HTML in
// place of JS and breaks the whole page) - so every exclusion is an explicit
// prefix check here instead of relying on the matcher regex.
function isPublicPath(pathname: string): boolean {
  if (pathname === "/login") return true;
  if (pathname === "/favicon.ico") return true;
  if (pathname.startsWith("/_next/")) return true;
  return false;
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const cookieValue = request.cookies.get(COOKIE_NAME)?.value;
  if (isValidSession(cookieValue)) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}

// api/* never reaches this service under Vercel Services routing. The
// matcher is intentionally broad (match everything) since isPublicPath()
// above does the real exclusion work.
export const proxyConfig = {
  matcher: ["/:path*"],
};
