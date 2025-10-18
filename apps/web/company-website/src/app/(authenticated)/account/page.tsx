"use client";

import { useAuth } from "@/contexts/AuthContext";

export default function AccountPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "40px",
        maxWidth: "1200px",
        margin: "0 auto",
      }}
    >
      <h1>Account Settings</h1>
      <p
        style={{
          fontSize: "18px",
          color: "#666",
          marginTop: "10px",
        }}
      >
        Manage your DataWoven account
      </p>

      {user && (
        <div
          style={{
            marginTop: "40px",
            display: "grid",
            gap: "30px",
          }}
        >
          {/* Account Information */}
          <div
            style={{
              padding: "30px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              backgroundColor: "#fff",
            }}
          >
            <h2
              style={{ marginTop: 0, marginBottom: "20px" }}
            >
              Account Information
            </h2>
            <div style={{ display: "grid", gap: "15px" }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    color: "#666",
                    marginBottom: "5px",
                  }}
                >
                  Email Address
                </label>
                <div
                  style={{
                    fontSize: "16px",
                    fontWeight: "500",
                  }}
                >
                  {user.email}
                </div>
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    color: "#666",
                    marginBottom: "5px",
                  }}
                >
                  User ID
                </label>
                <div
                  style={{
                    fontSize: "16px",
                    fontWeight: "500",
                    fontFamily: "monospace",
                  }}
                >
                  {user.userId}
                </div>
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    color: "#666",
                    marginBottom: "5px",
                  }}
                >
                  Account Type
                </label>
                <div
                  style={{
                    fontSize: "16px",
                    fontWeight: "500",
                  }}
                >
                  {user.groups.join(", ") ||
                    "Standard User"}
                </div>
              </div>
            </div>
          </div>

          {/* Subscription Information */}
          <div
            style={{
              padding: "30px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              backgroundColor: "#fff",
            }}
          >
            <h2
              style={{ marginTop: 0, marginBottom: "20px" }}
            >
              Subscription
            </h2>
            <p style={{ color: "#666", margin: 0 }}>
              Subscription management features coming soon.
            </p>
          </div>

          {/* Security Settings */}
          <div
            style={{
              padding: "30px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              backgroundColor: "#fff",
            }}
          >
            <h2
              style={{ marginTop: 0, marginBottom: "20px" }}
            >
              Security
            </h2>
            <div style={{ display: "grid", gap: "15px" }}>
              <button
                style={{
                  padding: "10px 16px",
                  backgroundColor: "#0070f3",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "14px",
                  fontWeight: "600",
                  cursor: "pointer",
                  width: "fit-content",
                }}
                onClick={() =>
                  (window.location.href =
                    "/forgot-password")
                }
              >
                Change Password
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
