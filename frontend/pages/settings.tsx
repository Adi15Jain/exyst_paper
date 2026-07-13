/**
 * Account settings — profile, password, and account deletion.
 */

import React, { useEffect, useState } from "react";
import Head from "next/head";
import { useRouter } from "next/router";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/lib/auth-context";
import { auth as authApi } from "@/lib/api";

const cardStyle: React.CSSProperties = {
    padding: "24px",
    marginBottom: 20,
};

const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: "0.8rem",
    fontWeight: 600,
    color: "var(--text-secondary)",
    marginBottom: 6,
};

const sectionTitle: React.CSSProperties = {
    margin: "0 0 4px",
    fontSize: "1rem",
    fontWeight: 700,
    color: "var(--text-primary)",
};

const sectionHint: React.CSSProperties = {
    margin: "0 0 20px",
    fontSize: "0.8rem",
    color: "var(--text-muted)",
};

function Banner({ kind, children }: { kind: "success" | "error"; children: React.ReactNode }) {
    const isError = kind === "error";
    return (
        <div
            role={isError ? "alert" : "status"}
            style={{
                marginTop: 16,
                padding: "10px 14px",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8rem",
                background: isError
                    ? "rgba(239, 68, 68, 0.1)"
                    : "rgba(34, 197, 94, 0.1)",
                border: `1px solid ${
                    isError ? "rgba(239, 68, 68, 0.2)" : "rgba(34, 197, 94, 0.2)"
                }`,
                color: isError ? "#ef4444" : "#22c55e",
            }}
        >
            {children}
        </div>
    );
}

export default function SettingsPage() {
    const router = useRouter();
    const { user, loading: authLoading, logout, refreshUser } = useAuth();

    const [name, setName] = useState("");
    const [savingName, setSavingName] = useState(false);
    const [nameMsg, setNameMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);

    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [savingPassword, setSavingPassword] = useState(false);
    const [pwMsg, setPwMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);

    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState<string | null>(null);

    useEffect(() => {
        if (authLoading) return;
        if (!user) {
            router.push("/login");
            return;
        }
        setName(user.name);
    }, [user, authLoading, router]);

    if (authLoading || !user) return null;

    const handleSaveName = async (e: React.FormEvent) => {
        e.preventDefault();
        setNameMsg(null);
        setSavingName(true);
        try {
            await authApi.updateProfile(name);
            await refreshUser();
            setNameMsg({ kind: "success", text: "Name updated." });
        } catch (err) {
            setNameMsg({
                kind: "error",
                text: err instanceof Error ? err.message : "Couldn't update your name.",
            });
        } finally {
            setSavingName(false);
        }
    };

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setPwMsg(null);
        setSavingPassword(true);
        try {
            await authApi.changePassword(currentPassword, newPassword);
            setCurrentPassword("");
            setNewPassword("");
            setPwMsg({
                kind: "success",
                text: "Password changed. Other devices have been signed out.",
            });
        } catch (err) {
            setPwMsg({
                kind: "error",
                text: err instanceof Error ? err.message : "Couldn't change your password.",
            });
        } finally {
            setSavingPassword(false);
        }
    };

    const handleDeleteAccount = async () => {
        const confirmation = window.prompt(
            "This permanently deletes your account, documents, analyses and predictions. " +
                'This cannot be undone.\n\nType DELETE to confirm.',
        );
        if (confirmation !== "DELETE") return;

        setDeleteError(null);
        setDeleting(true);
        try {
            await authApi.deleteAccount();
            logout();
            router.push("/");
        } catch (err) {
            setDeleteError(
                err instanceof Error ? err.message : "Couldn't delete your account.",
            );
            setDeleting(false);
        }
    };

    return (
        <>
            <Head>
                <title>Settings — Exyst</title>
                <meta name="description" content="Manage your Exyst account" />
            </Head>

            <AppLayout title="Settings">
                <div className="animate-fade-in" style={{ maxWidth: 640 }}>
                    {/* Profile */}
                    <form className="glass-card" style={cardStyle} onSubmit={handleSaveName}>
                        <h3 style={sectionTitle}>Profile</h3>
                        <p style={sectionHint}>Your name as it appears in the app.</p>

                        <label style={labelStyle} htmlFor="settings-email">
                            Email
                        </label>
                        <input
                            id="settings-email"
                            className="input-field"
                            value={user.email}
                            disabled
                            style={{ width: "100%", marginBottom: 16, opacity: 0.6 }}
                        />

                        <label style={labelStyle} htmlFor="settings-name">
                            Name
                        </label>
                        <input
                            id="settings-name"
                            className="input-field"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            maxLength={255}
                            style={{ width: "100%" }}
                        />

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={savingName || !name.trim() || name === user.name}
                            style={{ marginTop: 16 }}
                        >
                            {savingName ? "Saving…" : "Save changes"}
                        </button>

                        {nameMsg && <Banner kind={nameMsg.kind}>{nameMsg.text}</Banner>}
                    </form>

                    {/* Password */}
                    <form
                        className="glass-card"
                        style={cardStyle}
                        onSubmit={handleChangePassword}
                    >
                        <h3 style={sectionTitle}>Password</h3>
                        <p style={sectionHint}>
                            Changing your password signs you out on every other device.
                        </p>

                        <label style={labelStyle} htmlFor="current-password">
                            Current password
                        </label>
                        <input
                            id="current-password"
                            type="password"
                            className="input-field"
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                            required
                            autoComplete="current-password"
                            style={{ width: "100%", marginBottom: 16 }}
                        />

                        <label style={labelStyle} htmlFor="new-password">
                            New password
                        </label>
                        <input
                            id="new-password"
                            type="password"
                            className="input-field"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            required
                            minLength={8}
                            autoComplete="new-password"
                            style={{ width: "100%" }}
                        />
                        <p
                            style={{
                                margin: "6px 0 0",
                                fontSize: "0.7rem",
                                color: "var(--text-muted)",
                            }}
                        >
                            At least 8 characters.
                        </p>

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={
                                savingPassword ||
                                !currentPassword ||
                                newPassword.length < 8
                            }
                            style={{ marginTop: 16 }}
                        >
                            {savingPassword ? "Changing…" : "Change password"}
                        </button>

                        {pwMsg && <Banner kind={pwMsg.kind}>{pwMsg.text}</Banner>}
                    </form>

                    {/* Danger zone */}
                    <div
                        className="glass-card"
                        style={{
                            ...cardStyle,
                            borderColor: "rgba(239, 68, 68, 0.25)",
                        }}
                    >
                        <h3 style={{ ...sectionTitle, color: "#ef4444" }}>Delete account</h3>
                        <p style={sectionHint}>
                            Permanently deletes your account and every document, analysis and
                            prediction you own. This cannot be undone.
                        </p>

                        <button
                            onClick={handleDeleteAccount}
                            disabled={deleting}
                            style={{
                                background: "rgba(239, 68, 68, 0.12)",
                                border: "1px solid rgba(239, 68, 68, 0.3)",
                                color: "#ef4444",
                                cursor: deleting ? "wait" : "pointer",
                                fontSize: "0.85rem",
                                fontWeight: 600,
                                padding: "10px 18px",
                                borderRadius: "var(--radius-md)",
                            }}
                        >
                            {deleting ? "Deleting…" : "Delete my account"}
                        </button>

                        {deleteError && <Banner kind="error">{deleteError}</Banner>}
                    </div>
                </div>
            </AppLayout>
        </>
    );
}
