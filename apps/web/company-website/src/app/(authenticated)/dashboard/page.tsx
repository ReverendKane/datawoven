"use client";

import { useAuth } from "@/contexts/AuthContext";
import {
  useRouter,
  useSearchParams,
} from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const error = searchParams.get("error");
    if (error === "unauthorized") {
      setErrorMessage(
        "You do not have permission to access that page."
      );
      // Clear the error from URL after 5 seconds
      setTimeout(() => {
        setErrorMessage("");
        router.replace("/dashboard");
      }, 5000);
    }
  }, [searchParams, router]);

  // Debug log
  console.log("Dashboard - User data:", user);
  console.log("Dashboard - Loading:", loading);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

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
      {errorMessage && (
        <div
          style={{
            padding: "15px",
            marginBottom: "20px",
            backgroundColor: "#fee",
            border: "1px solid #fcc",
            borderRadius: "4px",
            color: "#c00",
          }}
        >
          {errorMessage}
        </div>
      )}
      <div>
        <h1>Dashboard</h1>
        <p
          style={{
            fontSize: "18px",
            color: "#666",
            marginTop: "10px",
          }}
        >
          Welcome to DataWoven
        </p>
      </div>

      {user && (
        <div
          style={{
            marginTop: "30px",
            padding: "20px",
            border: "1px solid #0070f3",
            borderRadius: "8px",
            backgroundColor: "#f0f8ff",
          }}
        >
          <h3 style={{ marginTop: 0, color: "#0070f3" }}>
            User Information
          </h3>
          <p>
            <strong>Email:</strong> {user.email}
          </p>
          <p>
            <strong>User ID:</strong> {user.userId}
          </p>
          <p>
            <strong>Groups:</strong>{" "}
            {user.groups.length > 0
              ? user.groups.join(", ")
              : "None"}
          </p>
        </div>
      )}

      <div
        style={{
          marginTop: "40px",
          padding: "30px",
          border: "1px solid #ddd",
          borderRadius: "8px",
          backgroundColor: "#f9f9f9",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Quick Links</h2>
        <ul style={{ lineHeight: "2", fontSize: "16px" }}>
          <li>
            <strong>Discovery Tools</strong> - Access your
            discovery assistant
          </li>
          <li>
            <strong>Implementation Portal</strong> - Manage
            your RAG systems
          </li>
          <li>
            <strong>Account Settings</strong> - Update your
            profile and preferences
          </li>
          <li>
            <strong>Billing</strong> - View subscription and
            usage
          </li>
        </ul>
      </div>
    </div>
  );
}
