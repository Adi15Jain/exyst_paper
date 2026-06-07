/**
 * Exyst API Client
 *
 * Centralized HTTP client with JWT token management,
 * automatic refresh, and typed responses.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

// --- Token Management ---

let accessToken: string | null = null;
let refreshToken: string | null = null;

if (typeof window !== "undefined") {
  accessToken = localStorage.getItem("exyst_access_token");
  refreshToken = localStorage.getItem("exyst_refresh_token");
}

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("exyst_access_token", access);
    localStorage.setItem("exyst_refresh_token", refresh);
  }
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("exyst_access_token");
    localStorage.removeItem("exyst_refresh_token");
  }
}

export function getAccessToken(): string | null {
  return accessToken;
}

// --- Core Fetch Wrapper ---

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const headers: HeadersInit = {
    ...(options.headers || {}),
  };

  // Don't set Content-Type for FormData (let browser set boundary)
  if (!(options.body instanceof FormData)) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }

  if (accessToken) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_V1}${path}`, {
    ...options,
    headers,
  });

  // Handle 401 — try refreshing token
  if (response.status === 401 && retry && refreshToken) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      return apiFetch<T>(path, options, false);
    }
    clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      message: `Request failed with status ${response.status}`,
    }));
    throw new Error(error.message || error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

async function tryRefreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_V1}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// --- Auth API ---

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
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
    const data = await apiFetch<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  me: () => apiFetch<User>("/auth/me"),

  logout: () => {
    clearTokens();
  },
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
    apiFetch<DocumentListResponse>(`/documents/?page=${page}&per_page=${perPage}`),

  get: (id: string) => apiFetch<DocumentData>(`/documents/${id}`),
};

// --- Analysis API ---

export interface AnalysisStatus {
  id: string;
  status: string;
  processing_time_seconds?: number;
  error_message?: string;
}

export interface AnalysisResult {
  id: string;
  document_id: string;
  status: string;
  syllabus_structure?: any;
  question_papers?: any[];
  topic_frequency?: any[];
  pattern_analysis?: any;
  num_pages_processed?: number;
  num_papers_found?: number;
  processing_time_seconds?: number;
  model_used?: string;
  created_at: string;
  completed_at?: string;
}

export const analysis = {
  run: (documentId: string) =>
    apiFetch<AnalysisStatus>(`/analysis/${documentId}/run`, { method: "POST" }),

  status: (documentId: string) =>
    apiFetch<AnalysisStatus>(`/analysis/${documentId}/status`),

  result: (documentId: string) =>
    apiFetch<AnalysisResult>(`/analysis/${documentId}/result`),
};

// --- Predictions API ---

export interface PredictionData {
  id: string;
  analysis_id: string;
  predicted_paper: any;
  confidence: any;
  overall_confidence: number;
  topic_coverage: Record<string, number>;
  model_used?: string;
  generation_time_seconds?: number;
  generated_at: string;
}

export const predictions = {
  generate: (documentId: string) =>
    apiFetch<PredictionData>(`/predictions/${documentId}/generate`, { method: "POST" }),

  get: (documentId: string) =>
    apiFetch<PredictionData>(`/predictions/${documentId}`),

  confidence: (documentId: string) =>
    apiFetch<any>(`/predictions/${documentId}/confidence`),
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
  topics: any[];
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
    apiFetch<TopicFrequencyData>(`/analytics/topic-frequency/${documentId}`),

  confidenceBreakdown: (documentId: string) =>
    apiFetch<any>(`/analytics/confidence-breakdown/${documentId}`),
};

// --- Health ---

export const health = {
  check: () => apiFetch<any>("/health"),
};
