import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Get auth tokens and user group from cookies
  const accessToken = request.cookies.get(
    "CognitoIdentityServiceProvider.accessToken"
  );
  const idToken = request.cookies.get(
    "CognitoIdentityServiceProvider.idToken"
  );
  const userGroup = request.cookies.get(
    "CognitoIdentityServiceProvider.userGroup"
  )?.value;

  // Check if user is authenticated
  const isAuthenticated = !!(accessToken && idToken);

  // Define protected routes
  const isAuthenticatedRoute =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/discovery") ||
    pathname.startsWith("/implementation") ||
    pathname.startsWith("/account") ||
    pathname.startsWith("/admin");

  const isAdminRoute = pathname.startsWith("/admin");

  const isPublicRoute =
    pathname.startsWith("/login") ||
    pathname.startsWith("/signup") ||
    pathname.startsWith("/forgot-password") ||
    pathname.startsWith("/reset-password") ||
    pathname === "/";

  // Redirect logic
  if (isAuthenticatedRoute && !isAuthenticated) {
    // User trying to access protected route without auth -> redirect to login
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Check admin routes - only DataWovenAdmin can access
  if (
    isAdminRoute &&
    isAuthenticated &&
    userGroup !== "DataWovenAdmin"
  ) {
    // Authenticated but not admin -> redirect to dashboard with error
    const dashboardUrl = new URL("/dashboard", request.url);
    dashboardUrl.searchParams.set("error", "unauthorized");
    return NextResponse.redirect(dashboardUrl);
  }

  if (
    isPublicRoute &&
    isAuthenticated &&
    pathname.startsWith("/login")
  ) {
    // Authenticated user trying to access login page -> redirect to dashboard
    return NextResponse.redirect(
      new URL("/dashboard", request.url)
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.png|.*\\.jpg|.*\\.svg).*)",
  ],
};
