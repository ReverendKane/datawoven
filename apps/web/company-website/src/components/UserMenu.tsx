"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useState, useEffect, useRef } from "react";

export default function UserMenu() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener(
      "mousedown",
      handleClickOutside
    );
    return () =>
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
  }, []);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  if (!user) return null;

  const isAdmin = user.groups.includes("DataWovenAdmin");
  const userInitials = user.email
    .substring(0, 2)
    .toUpperCase();

  return (
    <div className="user-menu-container" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="user-menu-button"
      >
        <div className="user-avatar">{userInitials}</div>
        <span>{user.email.split("@")[0]}</span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          className={
            isOpen ? "chevron-open" : "chevron-closed"
          }
        >
          <path
            d="M2 4l4 4 4-4"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="user-menu-dropdown">
          <div className="user-menu-header">
            <div className="user-email">{user.email}</div>
            <div className="user-group">
              {user.groups.join(", ") || "No group"}
            </div>
          </div>

          <div className="user-menu-links">
            <a
              href="/dashboard"
              onClick={() => setIsOpen(false)}
              className="menu-link"
            >
              Dashboard
            </a>

            <a
              href="/account"
              onClick={() => setIsOpen(false)}
              className="menu-link"
            >
              Account Settings
            </a>

            {isAdmin && (
              <a
                href="/admin/monitoring"
                onClick={() => setIsOpen(false)}
                className="menu-link"
              >
                Admin Panel
              </a>
            )}
          </div>

          <div className="user-menu-footer">
            <button
              onClick={handleLogout}
              className="logout-button"
            >
              Logout
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .user-menu-container {
          position: relative;
        }

        .user-menu-button {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background-color: #f0f0f0;
          border: 1px solid #ddd;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
        }

        .user-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background-color: #0070f3;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 12px;
        }

        .chevron-open {
          transform: rotate(180deg);
          transition: transform 0.2s;
        }

        .chevron-closed {
          transform: rotate(0deg);
          transition: transform 0.2s;
        }

        .user-menu-dropdown {
          position: absolute;
          top: 100%;
          right: 0;
          margin-top: 8px;
          background-color: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          min-width: 220px;
          z-index: 1000;
        }

        .user-menu-header {
          padding: 12px 16px;
          border-bottom: 1px solid #eee;
        }

        .user-email {
          font-size: 14px;
          font-weight: bold;
          margin-bottom: 4px;
        }

        .user-group {
          font-size: 12px;
          color: #666;
        }

        .user-menu-links {
          padding: 8px 0;
        }

        .menu-link {
          display: block;
          padding: 10px 16px;
          color: #333;
          text-decoration: none;
          font-size: 14px;
          cursor: pointer;
        }

        .menu-link:hover {
          background-color: #f5f5f5;
        }

        .user-menu-footer {
          padding: 8px 0;
          border-top: 1px solid #eee;
        }

        .logout-button {
          display: block;
          width: 100%;
          padding: 10px 16px;
          text-align: left;
          background-color: transparent;
          border: none;
          color: #dc3545;
          font-size: 14px;
          cursor: pointer;
          font-weight: 500;
        }

        .logout-button:hover {
          background-color: #fff5f5;
        }
      `}</style>
    </div>
  );
}
