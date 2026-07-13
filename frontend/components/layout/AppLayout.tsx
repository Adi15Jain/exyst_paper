/**
 * App Layout — sidebar navigation + top bar.
 * Used on all authenticated pages.
 */

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useAuth } from "@/lib/auth-context";

interface AppLayoutProps {
  children: React.ReactNode;
  title?: string;
}

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/upload", label: "Upload", icon: "📄" },
  { href: "/documents", label: "Documents", icon: "📁" },
  { href: "/analytics", label: "Analytics", icon: "📈" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export default function AppLayout({ children, title }: AppLayoutProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Close the mobile sidebar whenever navigation happens.
  useEffect(() => {
    setSidebarOpen(false);
  }, [router.pathname]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg-primary)" }}>
      {/* Mobile overlay — closes the sidebar on tap */}
      <div
        className={`sidebar-overlay${sidebarOpen ? " open" : ""}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside className={`app-sidebar${sidebarOpen ? " open" : ""}`}>
        {/* Logo */}
        <div
          style={{
            padding: "24px 20px",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <Link href="/dashboard" style={{ textDecoration: "none" }}>
            <h1
              className="text-gradient"
              style={{
                fontSize: "1.5rem",
                fontWeight: 900,
                letterSpacing: "-0.02em",
                margin: 0,
              }}
            >
              EXYST
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.7rem", marginTop: 4, letterSpacing: "0.05em" }}>
              EXAM INTELLIGENCE
            </p>
          </Link>
        </div>

        {/* Nav Items */}
        <nav style={{ flex: 1, padding: "16px 12px" }}>
          {navItems.map((item) => {
            const isActive = router.pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 14px",
                  borderRadius: "var(--radius-md)",
                  color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                  background: isActive ? "rgba(99, 102, 241, 0.1)" : "transparent",
                  textDecoration: "none",
                  fontSize: "0.875rem",
                  fontWeight: isActive ? 600 : 400,
                  marginBottom: 4,
                  transition: "all 0.2s ease",
                  borderLeft: isActive ? "3px solid var(--accent-indigo)" : "3px solid transparent",
                }}
              >
                <span style={{ fontSize: "1.1rem" }}>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User Section */}
        <div
          style={{
            padding: "16px 20px",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                background: "var(--gradient-main)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: "0.85rem",
              }}
            >
              {user?.name?.charAt(0)?.toUpperCase() || "?"}
            </div>
            <div style={{ overflow: "hidden" }}>
              <p
                style={{
                  color: "var(--text-primary)",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  margin: 0,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {user?.name || "User"}
              </p>
              <p
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.7rem",
                  margin: 0,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {user?.email || ""}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="btn-secondary"
            style={{ width: "100%", fontSize: "0.8rem", padding: "8px 12px" }}
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="app-main">
        {/* Top Bar */}
        <header
          className="glass"
          style={{
            padding: "16px 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            position: "sticky",
            top: 0,
            zIndex: 30,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              className="sidebar-toggle"
              aria-label={sidebarOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={sidebarOpen}
              onClick={() => setSidebarOpen((open) => !open)}
            >
              ☰
            </button>
            <h2
              style={{
                fontSize: "1.25rem",
                fontWeight: 700,
                margin: 0,
                color: "var(--text-primary)",
              }}
            >
              {title || "Dashboard"}
            </h2>
          </div>
        </header>

        {/* Page Content */}
        <div className="app-content">{children}</div>
      </main>
    </div>
  );
}
