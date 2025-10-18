"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { confirmSignIn } from "aws-amplify/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [needsPasswordChange, setNeedsPasswordChange] =
    useState(false);

  const router = useRouter();
  const { login, refreshUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await login(email, password);

      if (
        result?.nextStep?.signInStep ===
        "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED"
      ) {
        setNeedsPasswordChange(true);
      } else if (result?.isSignedIn) {
        await refreshUser();

        // Check for redirect parameter
        const searchParams = new URLSearchParams(
          window.location.search
        );
        const redirect =
          searchParams.get("redirect") || "/dashboard";
        router.push(redirect);
      }
    } catch (err: any) {
      console.error("Login error:", err);
      setError(
        err.message ||
          "Failed to sign in. Please check your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (
    e: React.FormEvent
  ) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (newPassword.length < 12) {
      setError("Password must be at least 12 characters");
      return;
    }

    setLoading(true);

    try {
      await confirmSignIn({
        challengeResponse: newPassword,
        options: {
          userAttributes: {
            name: email.split("@")[0],
          },
        },
      });
      await refreshUser();

      // Check for redirect parameter
      const searchParams = new URLSearchParams(
        window.location.search
      );
      const redirect =
        searchParams.get("redirect") || "/dashboard";
      router.push(redirect);
    } catch (err: any) {
      console.error("Password change error:", err);
      setError(err.message || "Failed to change password");
    } finally {
      setLoading(false);
    }
  };

  if (needsPasswordChange) {
    return (
      <div
        style={{
          maxWidth: "400px",
          margin: "100px auto",
          padding: "20px",
          border: "1px solid #ccc",
        }}
      >
        <h1>Change Password</h1>
        <p style={{ color: "#666", marginTop: "10px" }}>
          You must change your temporary password before
          continuing.
        </p>

        {error && (
          <div
            style={{
              padding: "10px",
              marginTop: "20px",
              backgroundColor: "#fee",
              border: "1px solid #fcc",
              borderRadius: "4px",
              color: "#c00",
            }}
          >
            {error}
          </div>
        )}

        <form
          onSubmit={handlePasswordChange}
          style={{ marginTop: "30px" }}
        >
          <div style={{ marginBottom: "20px" }}>
            <label
              style={{
                display: "block",
                marginBottom: "5px",
                fontWeight: "bold",
              }}
            >
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) =>
                setNewPassword(e.target.value)
              }
              placeholder="Enter new password (min 12 characters)"
              required
              disabled={loading}
              style={{
                width: "100%",
                padding: "10px",
                border: "1px solid #ddd",
                borderRadius: "4px",
              }}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label
              style={{
                display: "block",
                marginBottom: "5px",
                fontWeight: "bold",
              }}
            >
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) =>
                setConfirmPassword(e.target.value)
              }
              placeholder="Confirm new password"
              required
              disabled={loading}
              style={{
                width: "100%",
                padding: "10px",
                border: "1px solid #ddd",
                borderRadius: "4px",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              backgroundColor: loading ? "#ccc" : "#0070f3",
              color: "white",
              border: "none",
              borderRadius: "4px",
              fontSize: "16px",
              fontWeight: "bold",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading
              ? "Changing password..."
              : "Change Password"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: "400px",
        margin: "100px auto",
        padding: "20px",
        border: "1px solid #ccc",
      }}
    >
      <h1>Login to DataWoven</h1>

      {error && (
        <div
          style={{
            padding: "10px",
            marginTop: "20px",
            backgroundColor: "#fee",
            border: "1px solid #fcc",
            borderRadius: "4px",
            color: "#c00",
          }}
        >
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        style={{ marginTop: "30px" }}
      >
        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "5px",
              fontWeight: "bold",
            }}
          >
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            required
            disabled={loading}
            style={{
              width: "100%",
              padding: "10px",
              border: "1px solid #ddd",
              borderRadius: "4px",
            }}
          />
        </div>

        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "5px",
              fontWeight: "bold",
            }}
          >
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
            disabled={loading}
            style={{
              width: "100%",
              padding: "10px",
              border: "1px solid #ddd",
              borderRadius: "4px",
            }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px",
            backgroundColor: loading ? "#ccc" : "#0070f3",
            color: "white",
            border: "none",
            borderRadius: "4px",
            fontSize: "16px",
            fontWeight: "bold",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <div
        style={{ marginTop: "20px", textAlign: "center" }}
      >
        <a
          href="/forgot-password"
          style={{ color: "#0070f3" }}
        >
          Forgot password?
        </a>
      </div>
    </div>
  );
}
