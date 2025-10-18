"use client";

import { useAuth } from "@/contexts/AuthContext";

export default function AdminProvisioningPage() {
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
      <h1>Client Provisioning</h1>
      <p
        style={{
          fontSize: "18px",
          color: "#666",
          marginTop: "10px",
        }}
      >
        Create and manage client accounts and resources
      </p>

      <div
        style={{
          marginTop: "40px",
          display: "grid",
          gap: "30px",
        }}
      >
        {/* Create New Client */}
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
            Create New Client
          </h2>
          <p
            style={{ color: "#666", marginBottom: "20px" }}
          >
            Provision a new client account with Discovery or
            Implementation services.
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
            Start Provisioning Wizard
          </button>
        </div>

        {/* Active Clients */}
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
            Active Clients
          </h2>
          <p
            style={{ color: "#666", marginBottom: "20px" }}
          >
            View and manage existing client accounts.
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
            No active clients yet
          </div>
        </div>

        {/* Subscription Tiers */}
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
            Subscription Tiers
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(250px, 1fr))",
              gap: "20px",
              marginTop: "20px",
            }}
          >
            <div
              style={{
                padding: "20px",
                border: "1px solid #0070f3",
                borderRadius: "6px",
                backgroundColor: "#f0f8ff",
              }}
            >
              <h3
                style={{
                  marginTop: 0,
                  marginBottom: "10px",
                  color: "#0070f3",
                }}
              >
                Discovery Only
              </h3>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "20px",
                  color: "#666",
                  fontSize: "14px",
                }}
              >
                <li>Desktop app access</li>
                <li>1 Discovery report</li>
                <li>Session management</li>
              </ul>
            </div>
            <div
              style={{
                padding: "20px",
                border: "1px solid #0070f3",
                borderRadius: "6px",
                backgroundColor: "#f0f8ff",
              }}
            >
              <h3
                style={{
                  marginTop: 0,
                  marginBottom: "10px",
                  color: "#0070f3",
                }}
              >
                Implementation
              </h3>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "20px",
                  color: "#666",
                  fontSize: "14px",
                }}
              >
                <li>Everything in Discovery</li>
                <li>Custom RAG systems</li>
                <li>Web chat interface</li>
                <li>Compute credits</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
