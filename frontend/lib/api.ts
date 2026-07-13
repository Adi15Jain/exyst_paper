/**
 * Exyst API Client
 *
 * Centralized HTTP client with JWT token management,
 * automatic refresh, and typed responses.
 */

const getApiBase = (): string => {
    if (process.env.NEXT_PUBLIC_API_URL) {
        return process.env.NEXT_PUBLIC_API_URL;
    }
    if (typeof window !== "undefined") {
        // On Vercel (non-localhost), route API requests to the /_backend service route prefix
        if (
            window.location.hostname !== "localhost" &&
            !window.location.hostname.includes("127.0.0.1")
        ) {
            return "/_backend";
        }
    }
    return "http://localhost:8000";
};

const API_BASE = getApiBase();
const API_V1 = `${API_BASE}/api/v1`;

// --- Token Management ---
//
// The access token lives in memory only (30-min lifetime); the refresh token
// lives in an httpOnly cookie set by the backend, so script — including any
// injected XSS payload — can never read it. On a full page load the session
// is restored via auth.restore(), which exchanges the cookie for a fresh
// access token.

let accessToken: string | null = null;

export function setAccessToken(access: string) {
    accessToken = access;
}

export function clearAccessToken() {
    accessToken = null;
}

export function getAccessToken(): string | null {
    return accessToken;
}

// --- Core Fetch Wrapper ---

async function apiFetch<T>(
    path: string,
    options: RequestInit = {},
    retry = true,
): Promise<T> {
    const headers: HeadersInit = {
        ...(options.headers || {}),
    };

    // Don't set Content-Type for FormData (let browser set boundary)
    if (!(options.body instanceof FormData)) {
        (headers as Record<string, string>)["Content-Type"] =
            "application/json";
    }

    if (accessToken) {
        (headers as Record<string, string>)["Authorization"] =
            `Bearer ${accessToken}`;
    }

    const response = await fetch(`${API_V1}${path}`, {
        ...options,
        headers,
    });

    // Handle 401 — try refreshing via the httpOnly cookie. Never for the
    // credential endpoints: there a 401 means "wrong password" or "bad reset
    // token", not "expired session". Refreshing would be pointless, and on the
    // reset page it would bounce the user to /login instead of showing why.
    const CREDENTIAL_PATHS = [
        "/auth/login",
        "/auth/register",
        "/auth/change-password",
        "/auth/reset-password",
        "/auth/forgot-password",
    ];
    const isCredentialEndpoint = CREDENTIAL_PATHS.some((p) => path.startsWith(p));
    if (response.status === 401 && retry && !isCredentialEndpoint) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
            return apiFetch<T>(path, options, false);
        }
        clearAccessToken();
        if (
            typeof window !== "undefined" &&
            window.location.pathname !== "/login"
        ) {
            window.location.href = "/login";
        }
        throw new Error("Session expired. Please log in again.");
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({
            message: `Request failed with status ${response.status}`,
        }));
        throw new Error(
            error.message || error.detail || `API error: ${response.status}`,
        );
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

async function tryRefreshToken(): Promise<boolean> {
    try {
        // The refresh token travels in the httpOnly cookie; the rotated one
        // comes back the same way. Only the access token is in the body.
        const response = await fetch(`${API_V1}/auth/refresh`, {
            method: "POST",
            credentials: "include",
        });

        if (!response.ok) return false;

        const data = await response.json();
        setAccessToken(data.access_token);
        return true;
    } catch {
        return false;
    }
}

// --- Auth API ---

export interface LoginResponse {
    access_token: string;
    // The refresh token is delivered as an httpOnly cookie, never in the body.
    token_type: string;
}

export interface User {
    id: string;
    email: string;
    name: string;
    created_at: string;
}

export const auth = {
    register: (email: string, password: string, name: string) =>
        apiFetch<User>("/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password, name }),
        }),

    login: async (email: string, password: string): Promise<LoginResponse> => {
        // credentials: "include" so the backend's refresh cookie is stored
        // even when the API runs on another origin (local dev).
        const data = await apiFetch<LoginResponse>("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
            credentials: "include",
        });
        setAccessToken(data.access_token);
        return data;
    },

    me: () => apiFetch<User>("/auth/me"),

    /**
     * Restore the session after a full page load: exchange the httpOnly
     * refresh cookie for a fresh access token, then load the user.
     * Resolves null when there is no valid session.
     */
    restore: async (): Promise<User | null> => {
        const refreshed = await tryRefreshToken();
        if (!refreshed) return null;
        return apiFetch<User>("/auth/me");
    },

    logout: async (): Promise<void> => {
        try {
            // Revokes every outstanding refresh token and clears the cookie.
            await fetch(`${API_V1}/auth/logout`, {
                method: "POST",
                credentials: "include",
            });
        } catch {
            // Network failure shouldn't block local sign-out.
        }
        clearAccessToken();
    },

    updateProfile: (name: string) =>
        apiFetch<User>("/auth/me", {
            method: "PATCH",
            body: JSON.stringify({ name }),
        }),

    changePassword: (currentPassword: string, newPassword: string) =>
        apiFetch<void>("/auth/change-password", {
            method: "POST",
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
            }),
        }),

    deleteAccount: () =>
        apiFetch<void>("/auth/me", { method: "DELETE", credentials: "include" }),

    forgotPassword: (email: string) =>
        apiFetch<{ message: string }>("/auth/forgot-password", {
            method: "POST",
            body: JSON.stringify({ email }),
        }),

    resetPassword: (token: string, newPassword: string) =>
        apiFetch<void>("/auth/reset-password", {
            method: "POST",
            body: JSON.stringify({ token, new_password: newPassword }),
            credentials: "include",
        }),
};

// --- Documents API ---

export interface DocumentData {
    id: string;
    filename: string;
    original_filename: string;
    file_size_bytes: number;
    status: string;
    error_message?: string;
    uploaded_at: string;
    has_analysis?: boolean;
    has_prediction?: boolean;
}

export interface DocumentListResponse {
    documents: DocumentData[];
    total: number;
    page: number;
    per_page: number;
}

export const documents = {
    upload: (file: File) => {
        const formData = new FormData();
        formData.append("file", file);
        return apiFetch<DocumentData>("/documents/upload", {
            method: "POST",
            body: formData,
        });
    },

    list: (page = 1, perPage = 20) =>
        apiFetch<DocumentListResponse>(
            `/documents/?page=${page}&per_page=${perPage}`,
        ),

    get: (id: string) => apiFetch<DocumentData>(`/documents/${id}`),

    rename: (id: string, name: string) =>
        apiFetch<DocumentData>(`/documents/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ original_filename: name }),
        }),

    delete: (id: string) =>
        apiFetch<void>(`/documents/${id}`, { method: "DELETE" }),
};

// --- Analysis API ---

export interface AnalysisStatus {
    id: string;
    status: string;
    processing_time_seconds?: number;
    error_message?: string;
}

/** Mirrors backend app/schemas/analysis.py — keep in sync. */
export interface SyllabusUnit {
    unit_number?: number | string;
    title?: string;
    topics?: string[];
}

export interface SyllabusStructure {
    course_title?: string | null;
    units?: SyllabusUnit[];
    total_topics?: number;
}

export interface QuestionPaperSummary {
    academic_session?: string | null;
    session?: string;
    text?: string;
    total_questions?: number;
    max_marks?: number | null;
    topics_covered?: string[];
}

export interface TopicFrequency {
    topic: string;
    count: number;
    percentage: number;
    trend: "rising" | "falling" | "stable" | string;
}

export interface PatternAnalysis {
    subject?: string;
    max_marks?: number | string;
    duration?: string;
    typical_question_format?: string;
    [key: string]: unknown;
}

export interface AnalysisResult {
    id: string;
    document_id: string;
    status: string;
    syllabus_structure?: SyllabusStructure | null;
    question_papers?: QuestionPaperSummary[];
    topic_frequency?: TopicFrequency[];
    pattern_analysis?: PatternAnalysis | null;
    num_pages_processed?: number;
    num_papers_found?: number;
    processing_time_seconds?: number;
    model_used?: string;
    created_at: string;
    completed_at?: string;
}

export const analysis = {
    run: (documentId: string) =>
        apiFetch<AnalysisStatus>(`/analysis/${documentId}/run`, {
            method: "POST",
        }),

    status: (documentId: string) =>
        apiFetch<AnalysisStatus>(`/analysis/${documentId}/status`),

    result: (documentId: string) =>
        apiFetch<AnalysisResult>(`/analysis/${documentId}/result`),
};

// --- Predictions API ---

/** Mirrors backend app/schemas/prediction.py — keep in sync. */
export interface QuestionPart {
    label: string;
    question_text: string;
    marks: number;
}

export interface AlternativeQuestion {
    question_text: string;
    parts: QuestionPart[];
}

export interface PredictedQuestion {
    question_number: number;
    question_text: string;
    topic: string;
    marks: number;
    question_type: "short" | "medium" | "long";
    has_parts: boolean;
    parts: QuestionPart[];
    or_choice: AlternativeQuestion | null;
    confidence: number;
    reasoning: string;
}

export interface PredictedSection {
    section_name: string;
    title: string;
    description: string;
    questions: PredictedQuestion[];
    total_marks: number;
}

export interface PaperInfo {
    title?: string;
    subject?: string;
    academic_year?: string;
    duration?: string;
    max_marks?: string | number;
    instructions?: string[];
}

export interface PredictedPaper {
    paper_info: PaperInfo;
    sections: PredictedSection[];
    total_questions: number;
    topic_coverage: Record<string, number>;
    overall_confidence: number;
    is_fallback: boolean;
    error_message: string | null;
}

export interface PerQuestionConfidence {
    question_number?: number;
    question_text?: string;
    topic?: string;
    confidence?: number;
    [key: string]: unknown;
}

export interface ConfidenceReport {
    overall_confidence: number;
    topic_coverage_score: number;
    historical_alignment_score: number;
    question_quality_score: number;
    marks_distribution_score: number;
    per_question_confidence: PerQuestionConfidence[];
}

export interface PredictionData {
    id: string;
    analysis_id: string;
    predicted_paper: PredictedPaper;
    confidence: ConfidenceReport | null;
    overall_confidence: number;
    topic_coverage: Record<string, number>;
    model_used?: string;
    generation_time_seconds?: number;
    generated_at: string;
}

export const predictions = {
    generate: (documentId: string) =>
        apiFetch<PredictionData>(`/predictions/${documentId}/generate`, {
            method: "POST",
        }),

    get: (documentId: string) =>
        apiFetch<PredictionData>(`/predictions/${documentId}`),
};

// --- Analytics API ---

export interface OverviewStats {
    documents: { total: number };
    analyses: {
        total: number;
        completed: number;
        avg_processing_time_seconds: number;
        total_pages_processed: number;
        total_papers_found: number;
    };
    predictions: {
        total: number;
        avg_confidence: number;
        max_confidence: number;
        avg_generation_time_seconds: number;
    };
}

export interface TopicFrequencyData {
    topics: TopicFrequency[];
    chart_data: {
        labels: string[];
        values: number[];
        percentages: number[];
        trends: string[];
        colors: string[];
    };
}

export const analytics = {
    overview: () => apiFetch<OverviewStats>("/analytics/overview"),

    topicFrequency: (documentId: string) =>
        apiFetch<TopicFrequencyData>(
            `/analytics/topic-frequency/${documentId}`,
        ),
};

// --- Pipeline Streaming API (SSE) ---

export interface PipelineEvent {
    event: "stage" | "complete" | "error";
    data: {
        stage?: string;
        progress?: number;
        detail?: string;
        document_id?: string;
        prediction_id?: string;
        overall_confidence?: number;
        generation_time_seconds?: number;
        error?: string;
    };
}

export const pipeline = {
    /**
     * Run the full analysis + prediction pipeline with SSE streaming progress.
     * Calls onEvent for each SSE event received.
     * Returns a promise that resolves when the stream completes.
     */
    runStream: async (
        documentId: string,
        onEvent: (event: PipelineEvent) => void,
    ): Promise<void> => {
        const headers: Record<string, string> = {};
        if (accessToken) {
            headers["Authorization"] = `Bearer ${accessToken}`;
        }

        const response = await fetch(
            `${API_V1}/pipeline/${documentId}/run-stream`,
            {
                method: "POST",
                headers,
            },
        );

        if (!response.ok) {
            const error = await response.json().catch(() => ({
                message: `Pipeline failed with status ${response.status}`,
            }));
            throw new Error(
                error.message || error.detail || `Pipeline error: ${response.status}`,
            );
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE events from buffer
            const lines = buffer.split("\n");
            buffer = lines.pop() || ""; // Keep incomplete line in buffer

            let currentEvent = "";
            for (const line of lines) {
                if (line.startsWith("event: ")) {
                    currentEvent = line.slice(7).trim();
                } else if (line.startsWith("data: ")) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        onEvent({
                            event: currentEvent as PipelineEvent["event"],
                            data,
                        });
                    } catch {
                        // Skip malformed JSON
                    }
                }
            }
        }
    },
};
