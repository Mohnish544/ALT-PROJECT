// MedLens API Service Layer
// All backend communication is centralized here.
// Backend base URL is proxied via Vite dev server in development.

import type {
  Document,
  ProcessingJob,
  SystemStatus,
  EvaluationResult,
  AppSettings,
  SourceType,
  SourceChunk,
  RetrievalInfo,
} from '../types';

const BASE = '/api';

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }

  // Handle 204 no content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Documents ──────────────────────────────────────────────────────────────

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export const documentsApi = {
  list: (): Promise<DocumentListResponse> =>
    request('/documents'),

  get: (docId: string): Promise<Document> =>
    request(`/documents/${docId}`),

  delete: (docId: string): Promise<{ doc_id: string; message: string }> =>
    request(`/documents/${docId}`, { method: 'DELETE' }),

  upload: async (
    file: File,
    onProgress?: (stage: string) => void,
  ): Promise<ProcessingJob> => {
    const form = new FormData();
    form.append('file', file);

    const res = await fetch(`${BASE}/upload`, {
      method: 'POST',
      body: form,
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch { /* ignore */ }
      throw new ApiError(res.status, detail);
    }

    return res.json() as Promise<ProcessingJob>;
  },
};

// ── Chat ───────────────────────────────────────────────────────────────────

export interface ChatApiRequest {
  question: string;
  session_id: string;
  doc_ids?: string[];
  top_k?: number;
  fallback_threshold?: number;
}

export interface ChatApiResponse {
  session_id: string;
  question: string;
  answer: string;
  source_type: SourceType;
  sources: SourceChunk[];
  retrieval_info: RetrievalInfo;
  provider: string;
  model: string;
  error?: string;
}

export interface HistoryApiResponse {
  session_id: string;
  messages: { role: string; content: string }[];
  turn_count: number;
}

export const chatApi = {
  ask: (req: ChatApiRequest): Promise<ChatApiResponse> =>
    request('/chat', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  history: (sessionId: string): Promise<HistoryApiResponse> =>
    request(`/chat/history/${sessionId}`),

  clearHistory: (sessionId: string): Promise<{ message: string }> =>
    request(`/chat/history/${sessionId}`, { method: 'DELETE' }),
};

// ── Status ─────────────────────────────────────────────────────────────────

export const statusApi = {
  get: (): Promise<SystemStatus> => request('/status'),
};

// ── Evaluation ─────────────────────────────────────────────────────────────

export const evaluationApi = {
  run: (): Promise<EvaluationResult> => request('/evaluate'),
};

// ── Settings ───────────────────────────────────────────────────────────────

export const settingsApi = {
  get: (): Promise<AppSettings> => request('/settings'),
  update: (data: Partial<AppSettings>): Promise<AppSettings> =>
    request('/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};

export { ApiError };
