"use client";

import { useState } from "react";
import { resetPassword } from "aws-amplify/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await resetPassword({ username: email });
      setSuccess(true);
    } catch (err: any) {
      console.error("Reset password error:", err);
      setError(
        err.message ||
          "Failed to send reset code. Please try again."
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
        <h1>Check Your Email</h1>
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
            We've sent a password reset code to{" "}
            <strong>{email}</strong>
          </p>
          <p style={{ marginTop: "15px", marginBottom: 0 }}>
            Please check your email and use the code to
            reset your password.
          </p>
        </div>
        <div
          style={{ marginTop: "30px", textAlign: "center" }}
        >
          <a
            href={`/reset-password?email=${encodeURIComponent(email)}`}
            style={{
              display: "inline-block",
              padding: "12px 24px",
              backgroundColor: "#0070f3",
              color: "white",
              textDecoration: "none",
              borderRadius: "4px",
              fontWeight: "bold",
            }}
          >
            Enter Reset Code
          </a>
        </div>
        <div
          style={{ marginTop: "20px", textAlign: "center" }}
        >
          <a href="/login" style={{ color: "#0070f3" }}>
            Back to login
          </a>
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
      <h1>Forgot Password</h1>
      <p style={{ color: "#666", marginTop: "10px" }}>
        Enter your email address and we'll send you a code
        to reset your password.
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
          {loading ? "Sending..." : "Send Reset Code"}
        </button>
      </form>

      <div
        style={{ marginTop: "20px", textAlign: "center" }}
      >
        <a href="/login" style={{ color: "#0070f3" }}>
          Back to login
        </a>
      </div>
    </div>
  );
}
