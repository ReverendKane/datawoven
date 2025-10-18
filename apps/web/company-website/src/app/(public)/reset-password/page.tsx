"use client";

import { useState, useEffect } from "react";
import {
  useRouter,
  useSearchParams,
} from "next/navigation";
import { confirmResetPassword } from "aws-amplify/auth";

export default function ResetPasswordPage() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Pre-fill email if passed from forgot-password page
    const emailParam = searchParams.get("email");
    if (emailParam) {
      setEmail(emailParam);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validation
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
      await confirmResetPassword({
        username: email,
        confirmationCode: code,
        newPassword: newPassword,
      });
      setSuccess(true);

      // Redirect to login after 2 seconds
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err: any) {
      console.error("Confirm reset password error:", err);
      setError(
        err.message ||
          "Failed to reset password. Please check your code and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div
        style={{
          maxWidth: "500px",
          margin: "100px auto",
          padding: "30px",
          border: "1px solid #ccc",
        }}
      >
        <h1>Password Reset Successful!</h1>
        <div
          style={{
            marginTop: "20px",
            padding: "20px",
            backgroundColor: "#d4edda",
            border: "1px solid #c3e6cb",
            borderRadius: "4px",
            color: "#155724",
          }}
        >
          <p style={{ margin: 0, lineHeight: "1.6" }}>
            Your password has been successfully reset.
          </p>
          <p style={{ marginTop: "15px", marginBottom: 0 }}>
            Redirecting you to login...
          </p>
        </div>
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
      <h1>Reset Password</h1>
      <p style={{ color: "#666", marginTop: "10px" }}>
        Enter the code sent to your email and choose a new
        password.
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
            Email Address
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
            Verification Code
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Enter 6-digit code"
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
            New Password
          </label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
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
          <small
            style={{ color: "#666", fontSize: "12px" }}
          >
            Must be at least 12 characters with uppercase,
            lowercase, number, and special character
          </small>
        </div>

        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              marginBottom: "5px",
              fontWeight: "bold",
            }}
          >
            Confirm New Password
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
          {loading ? "Resetting..." : "Reset Password"}
        </button>
      </form>

      <div
        style={{ marginTop: "20px", textAlign: "center" }}
      >
        <a
          href="/forgot-password"
          style={{ color: "#0070f3", marginRight: "20px" }}
        >
          Resend code
        </a>
        <a href="/login" style={{ color: "#0070f3" }}>
          Back to login
        </a>
      </div>
    </div>
  );
}
