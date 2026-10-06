// Settings page — configuration display + info about the running system
import React, { useEffect } from 'react';
import { Header } from '../components/layout/Header';
import { statusApi } from '../services/api';
import { useStore } from '../store';

export default function Settings() {
  const { systemStatus, setSystemStatus } = useStore();

  useEffect(() => {
    statusApi.get().then(setSystemStatus).catch(() => {});
  }, [setSystemStatus]);

  const rows = systemStatus ? [
    { label: 'Embedding model',     value: systemStatus.embedding_model },
    { label: 'LLM provider',        value: systemStatus.llm_provider },
    { label: 'LLM model',           value: systemStatus.llm_model },
    { label: 'Documents indexed',   value: String(systemStatus.document_count) },
    { label: 'KB available',        value: systemStatus.kb_available ? 'Yes' : 'No' },
    { label: 'KB chunks',           value: systemStatus.kb_available ? systemStatus.kb_chunk_count.toLocaleString() : '—' },
    { label: 'System status',       value: systemStatus.status },
  ] : [];

  const envRows = [
    { key: 'LLM_PROVIDER',          desc: 'openai | anthropic | ollama | mock' },
    { key: 'OPENAI_API_KEY',         desc: 'Required when LLM_PROVIDER=openai' },
    { key: 'ANTHROPIC_API_KEY',      desc: 'Required when LLM_PROVIDER=anthropic' },
    { key: 'OLLAMA_BASE_URL',        desc: 'Ollama server URL (default: http://localhost:11434)' },
    { key: 'EMBEDDING_MODEL',        desc: 'Sentence-transformer model name' },
    { key: 'CHUNK_SIZE',             desc: 'Target tokens per chunk (default: 400)' },
    { key: 'CHUNK_OVERLAP',          desc: 'Overlap tokens (default: 50)' },
    { key: 'TOP_K',                  desc: 'Passages retrieved per query (default: 5)' },
    { key: 'DOC_FALLBACK_THRESHOLD', desc: 'Min score before KB fallback (default: 0.35)' },
    { key: 'LOG_LEVEL',              desc: 'info | debug | warning' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Header title="Settings" subtitle="System configuration and runtime values" />

      <div className="page-content">
        {/* Runtime values */}
        <div className="settings-group">
          <div className="settings-group-header">
            <div className="settings-group-title">Runtime Configuration</div>
          </div>
          {rows.length === 0 ? (
            <div style={{ padding: 'var(--space-4)', display: 'flex', gap: 'var(--space-2)' }}>
              <div className="spinner" />
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>Loading...</span>
            </div>
          ) : (
            rows.map(r => (
              <div key={r.label} className="settings-row">
                <div>
                  <div className="settings-row-label">{r.label}</div>
                </div>
                <div className="settings-row-value">
                  <span style={{ fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>
                    {r.value}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* .env configuration reference */}
        <div className="settings-group">
          <div className="settings-group-header">
            <div className="settings-group-title">.env Configuration Reference</div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: 2 }}>
              Copy .env.example → .env and set values before starting the backend
            </div>
          </div>
          {envRows.map(r => (
            <div key={r.key} className="settings-row">
              <div>
                <div className="settings-row-label" style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}>
                  {r.key}
                </div>
                <div className="settings-row-desc">{r.desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick start commands */}
        <div className="settings-group">
          <div className="settings-group-header">
            <div className="settings-group-title">Quick Start Commands</div>
          </div>
          {[
            { label: 'Install backend dependencies', cmd: 'pip install -r requirements.txt' },
            { label: 'Download MedQuAD (optional)',  cmd: 'python scripts/download_medquad.py --max-entries 2000' },
            { label: 'Build knowledge base index',  cmd: 'python scripts/build_kb_index.py' },
            { label: 'Start backend API',            cmd: 'python -m backend.api.main' },
            { label: 'Run tests',                   cmd: 'pytest backend/tests/' },
            { label: 'Install frontend dependencies',cmd: 'cd frontend && npm install' },
            { label: 'Start frontend dev server',   cmd: 'cd frontend && npm run dev' },
          ].map(r => (
            <div key={r.label} className="settings-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 'var(--space-1)' }}>
              <div className="settings-row-desc">{r.label}</div>
              <code style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', background: 'var(--color-bg-code)', padding: '3px 8px', borderRadius: 'var(--radius-sm)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border-subtle)' }}>
                {r.cmd}
              </code>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
