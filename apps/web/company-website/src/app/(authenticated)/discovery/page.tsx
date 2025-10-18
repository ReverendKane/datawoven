"use client";

import { useAuth } from "@/contexts/AuthContext";

export default function DiscoveryPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <p>Loading...</p>
      </div>
    );
  }

  const hasDiscoveryAccess =
    user?.groups.includes("DiscoveryAdmin") ||
    user?.groups.includes("DataWovenAdmin");

  return (
    <div
      style={{
        padding: "40px",
        maxWidth: "1200px",
        margin: "0 auto",
      }}
    >
      <h1>Discovery Tools</h1>
      <p
        style={{
          fontSize: "18px",
          color: "#666",
          marginTop: "10px",
        }}
      >
        AI-powered business process discovery and analysis
      </p>

      {!hasDiscoveryAccess ? (
        <div
          style={{
            marginTop: "40px",
            padding: "30px",
            border: "1px solid #fcc",
            borderRadius: "8px",
            backgroundColor: "#fff5f5",
          }}
        >
          <h3 style={{ marginTop: 0, color: "#c00" }}>
            Access Restricted
          </h3>
          <p style={{ margin: 0, color: "#666" }}>
            You don't have access to Discovery tools. Please
            contact your administrator or upgrade your
            subscription.
          </p>
        </div>
      ) : (
        <div
          style={{
            marginTop: "40px",
            display: "grid",
            gap: "30px",
          }}
        >
          {/* Discovery Assistant */}
          <div
            style={{
              padding: "30px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              backgroundColor: "#fff",
            }}
          >
            <h2
              style={{ marginTop: 0, marginBottom: "15px" }}
            >
              Discovery Assistant
            </h2>
            <p
              style={{
                color: "#666",
                marginBottom: "20px",
              }}
            >
              Desktop application for guided business
              process analysis and automation opportunity
              identification.
            </p>
            <button
              style={{
                padding: "10px 20px",
                backgroundColor: "#0070f3",
                color: "white",
                border: "none",
                borderRadius: "6px",
                fontSize: "14px",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              Download Desktop App
            </button>
          </div>

          {/* Session Management */}
          <div
            style={{
              padding: "30px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              backgroundColor: "#fff",
            }}
          >
            <h2
              style={{ marginTop: 0, marginBottom: "15px" }}
            >
              Session Management
            </h2>
            <p
              style={{
                color: "#666",
                marginBottom: "20px",
              }}
            >
              Create and manage respondent access codes for
              your discovery sessions.
            </p>
            <button
              style={{
                padding: "10px 20px",
                backgroundColor: "#0070f3",
                color: "white",
                border: "none",
                borderRadius: "6px",
                fontSize: "14px",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              Manage Sessions
            </button>
          </div>

          {/* Discovery Reports */}
          <div
            style={{
              padding: "30px",
              border: "1px solid #ddd",
              borderRadius: "8px",
              backgroundColor: "#fff",
            }}
          >
            <h2
              style={{ marginTop: 0, marginBottom: "15px" }}
            >
              Discovery Reports
            </h2>
            <p
              style={{
                color: "#666",
                marginBottom: "20px",
              }}
            >
              View and download your completed discovery
              analysis reports.
            </p>
            <div
              style={{
                padding: "20px",
                backgroundColor: "#f9f9f9",
                borderRadius: "6px",
                textAlign: "center",
                color: "#666",
              }}
            >
              No reports available yet
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
