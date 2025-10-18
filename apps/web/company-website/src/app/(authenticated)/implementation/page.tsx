"use client";

import { useAuth } from "@/contexts/AuthContext";

export default function ImplementationPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        <p>Loading...</p>
      </div>
    );
  }

  const hasImplementationAccess =
    user?.groups.includes("ImplementationUser") ||
    user?.groups.includes("DataWovenAdmin");

  return (
    <div
      style={{
        padding: "40px",
        maxWidth: "1200px",
        margin: "0 auto",
      }}
    >
      <h1>Implementation Portal</h1>
      <p
        style={{
          fontSize: "18px",
          color: "#666",
          marginTop: "10px",
        }}
      >
        Access your custom RAG systems and agentic tools
      </p>

      {!hasImplementationAccess ? (
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
            You don't have access to Implementation
            services. Please contact your administrator or
            upgrade your subscription.
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
          {/* Web Chat Interface */}
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
              AI Chat Interface
            </h2>
            <p
              style={{
                color: "#666",
                marginBottom: "20px",
              }}
            >
              Interact with your custom RAG systems and
              agentic tools through our web-based chat
              interface.
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
              Open Chat Interface
            </button>
          </div>

          {/* Document Management */}
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
              Document Management
            </h2>
            <p
              style={{
                color: "#666",
                marginBottom: "20px",
              }}
            >
              Upload and manage documents for your RAG
              knowledge base.
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
              Manage Documents
            </button>
          </div>

          {/* Analytics */}
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
              Usage Analytics
            </h2>
            <p
              style={{
                color: "#666",
                marginBottom: "20px",
              }}
            >
              Monitor your RAG system usage, query
              performance, and compute credits.
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "20px",
                marginTop: "20px",
              }}
            >
              <div
                style={{
                  padding: "20px",
                  backgroundColor: "#f0f8ff",
                  borderRadius: "6px",
                  border: "1px solid #0070f3",
                }}
              >
                <div
                  style={{
                    fontSize: "12px",
                    color: "#666",
                    marginBottom: "5px",
                  }}
                >
                  Queries This Month
                </div>
                <div
                  style={{
                    fontSize: "24px",
                    fontWeight: "bold",
                    color: "#0070f3",
                  }}
                >
                  -
                </div>
              </div>
              <div
                style={{
                  padding: "20px",
                  backgroundColor: "#f0f8ff",
                  borderRadius: "6px",
                  border: "1px solid #0070f3",
                }}
              >
                <div
                  style={{
                    fontSize: "12px",
                    color: "#666",
                    marginBottom: "5px",
                  }}
                >
                  Compute Credits
                </div>
                <div
                  style={{
                    fontSize: "24px",
                    fontWeight: "bold",
                    color: "#0070f3",
                  }}
                >
                  -
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
