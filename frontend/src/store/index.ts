// Zustand global store
// Manages: documents, chat sessions, system status, toasts, theme, UI state

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  Document,
  ChatMessage,
  ChatSession,
  SystemStatus,
  Toast,
} from '../types';

// Tiny uuid replacement using crypto.randomUUID (available in modern browsers)
function genId(): string {
  try { return crypto.randomUUID(); }
  catch { return Math.random().toString(36).slice(2); }
}

interface AppStore {
  // ── Theme ────────────────────────────────────────────────
  theme: 'light' | 'dark';
  setTheme: (t: 'light' | 'dark') => void;
  toggleTheme: () => void;

  // ── Sidebar ──────────────────────────────────────────────
  sidebarCollapsed: boolean;
  mobileNavOpen: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  toggleSidebar: () => void;
  setMobileNavOpen: (v: boolean) => void;

  // ── Documents ────────────────────────────────────────────
  documents: Document[];
  setDocuments: (docs: Document[]) => void;
  addDocument: (doc: Document) => void;
  updateDocument: (docId: string, updates: Partial<Document>) => void;
  removeDocument: (docId: string) => void;

  // ── Chat sessions ────────────────────────────────────────
  sessions: Record<string, ChatSession>;
  activeSessionId: string;
  createSession: (docIds?: string[]) => string;
  setActiveSession: (id: string) => void;
  addMessage: (sessionId: string, msg: ChatMessage) => void;
  updateMessage: (sessionId: string, msgId: string, updates: Partial<ChatMessage>) => void;
  clearSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;

  // ── Selected docs for chat ───────────────────────────────
  selectedDocIds: string[];
  setSelectedDocIds: (ids: string[]) => void;
  toggleDocSelection: (id: string) => void;

  // ── System status ────────────────────────────────────────
  systemStatus: SystemStatus | null;
  setSystemStatus: (s: SystemStatus) => void;

  // ── Toasts ───────────────────────────────────────────────
  toasts: Toast[];
  addToast: (t: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

export const useStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // ── Theme ──────────────────────────────────────────────
      theme: 'light',
      setTheme: (t) => {
        set({ theme: t });
        document.documentElement.setAttribute('data-theme', t);
      },
      toggleTheme: () => {
        const next = get().theme === 'light' ? 'dark' : 'light';
        get().setTheme(next);
      },

      // ── Sidebar ────────────────────────────────────────────
      sidebarCollapsed: false,
      mobileNavOpen: false,
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setMobileNavOpen: (v) => set({ mobileNavOpen: v }),

      // ── Documents ──────────────────────────────────────────
      documents: [],
      setDocuments: (docs) => set({ documents: docs }),
      addDocument: (doc) =>
        set((s) => ({ documents: [doc, ...s.documents.filter(d => d.doc_id !== doc.doc_id)] })),
      updateDocument: (docId, updates) =>
        set((s) => ({
          documents: s.documents.map(d => d.doc_id === docId ? { ...d, ...updates } : d),
        })),
      removeDocument: (docId) =>
        set((s) => ({ documents: s.documents.filter(d => d.doc_id !== docId) })),

      // ── Chat sessions ──────────────────────────────────────
      sessions: {},
      activeSessionId: '',
      createSession: (docIds = []) => {
        const id = genId();
        const session: ChatSession = {
          session_id: id,
          messages: [],
          created_at: new Date().toISOString(),
          doc_ids: docIds,
        };
        set((s) => ({
          sessions: { ...s.sessions, [id]: session },
          activeSessionId: id,
        }));
        return id;
      },
      setActiveSession: (id) => set({ activeSessionId: id }),
      addMessage: (sessionId, msg) =>
        set((s) => {
          const session = s.sessions[sessionId];
          if (!session) return s;
          return {
            sessions: {
              ...s.sessions,
              [sessionId]: { ...session, messages: [...session.messages, msg] },
            },
          };
        }),
      updateMessage: (sessionId, msgId, updates) =>
        set((s) => {
          const session = s.sessions[sessionId];
          if (!session) return s;
          return {
            sessions: {
              ...s.sessions,
              [sessionId]: {
                ...session,
                messages: session.messages.map(m => m.id === msgId ? { ...m, ...updates } : m),
              },
            },
          };
        }),
      clearSession: (sessionId) =>
        set((s) => {
          const session = s.sessions[sessionId];
          if (!session) return s;
          return {
            sessions: { ...s.sessions, [sessionId]: { ...session, messages: [] } },
          };
        }),
      deleteSession: (sessionId) =>
        set((s) => {
          const { [sessionId]: _, ...rest } = s.sessions;
          return {
            sessions: rest,
            activeSessionId: s.activeSessionId === sessionId ? '' : s.activeSessionId,
          };
        }),

      // ── Selected docs ──────────────────────────────────────
      selectedDocIds: [],
      setSelectedDocIds: (ids) => set({ selectedDocIds: ids }),
      toggleDocSelection: (id) =>
        set((s) => ({
          selectedDocIds: s.selectedDocIds.includes(id)
            ? s.selectedDocIds.filter(x => x !== id)
            : [...s.selectedDocIds, id],
        })),

      // ── System status ──────────────────────────────────────
      systemStatus: null,
      setSystemStatus: (s) => set({ systemStatus: s }),

      // ── Toasts ────────────────────────────────────────────
      toasts: [],
      addToast: (t) => {
        const id = genId();
        set((s) => ({ toasts: [...s.toasts, { ...t, id }] }));
        setTimeout(() => get().removeToast(id), 4000);
      },
      removeToast: (id) =>
        set((s) => ({ toasts: s.toasts.filter(t => t.id !== id) })),
    }),
    {
      name: 'medlens-store',
      partialize: (s) => ({
        theme: s.theme,
        sidebarCollapsed: s.sidebarCollapsed,
        sessions: s.sessions,
        activeSessionId: s.activeSessionId,
        selectedDocIds: s.selectedDocIds,
      }),
    },
  ),
);

// Apply persisted theme on load
const savedTheme = useStore.getState().theme;
document.documentElement.setAttribute('data-theme', savedTheme);
