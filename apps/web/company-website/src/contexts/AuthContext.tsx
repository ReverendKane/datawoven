"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  getCurrentUser,
  signIn,
  signOut,
  fetchAuthSession,
  fetchUserAttributes,
} from "aws-amplify/auth";
import { Amplify } from "aws-amplify";

// Configure Amplify for client-side
Amplify.configure(
  {
    Auth: {
      Cognito: {
        userPoolId:
          process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ||
          "",
        userPoolClientId:
          process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID ||
          "",
      },
    },
  },
  { ssr: true }
);

interface User {
  email: string;
  userId: string;
  groups: string[];
  attributes: Record<string, any>;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<any>; // ← NEW (returns SignInOutput)
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<
  AuthContextType | undefined
>(undefined);

// Helper to set auth cookies
function setAuthCookies(tokens: any) {
  if (typeof window !== "undefined") {
    const accessToken = tokens?.accessToken?.toString();
    const idToken = tokens?.idToken?.toString();
    const groups =
      tokens?.accessToken?.payload["cognito:groups"] || [];
    const primaryGroup = groups[0] || "none"; // Get first group (highest precedence)

    if (accessToken && idToken) {
      document.cookie = `CognitoIdentityServiceProvider.accessToken=${accessToken}; path=/; max-age=3600; SameSite=Lax`;
      document.cookie = `CognitoIdentityServiceProvider.idToken=${idToken}; path=/; max-age=3600; SameSite=Lax`;
      document.cookie = `CognitoIdentityServiceProvider.userGroup=${primaryGroup}; path=/; max-age=3600; SameSite=Lax`;
    }
  }
}

// Helper to clear auth cookies
function clearAuthCookies() {
  if (typeof window !== "undefined") {
    document.cookie =
      "CognitoIdentityServiceProvider.accessToken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.cookie =
      "CognitoIdentityServiceProvider.idToken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.cookie =
      "CognitoIdentityServiceProvider.userGroup=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
}

export function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const currentUser = await getCurrentUser();
      const session = await fetchAuthSession();
      const attributes = await fetchUserAttributes();

      const groups =
        (session.tokens?.accessToken?.payload[
          "cognito:groups"
        ] as string[]) || [];

      console.log(
        "RefreshUser - Current user:",
        currentUser
      );
      console.log("RefreshUser - Session:", session);
      console.log("RefreshUser - Groups:", groups);

      // Set auth cookies for middleware
      setAuthCookies(session.tokens);

      setUser({
        email:
          attributes.email ||
          currentUser.signInDetails?.loginId ||
          "",
        userId: currentUser.userId,
        groups,
        attributes,
      });
    } catch (error) {
      console.error("RefreshUser error:", error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const result = await signIn({
        username: email,
        password,
      });
      console.log("Login result:", result);
      return result; // ← RETURN the result instead
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await signOut();
      clearAuthCookies(); // ← Add this line
      setUser(null);
    } catch (error) {
      console.error("Logout error:", error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error(
      "useAuth must be used within an AuthProvider"
    );
  }
  return context;
}
