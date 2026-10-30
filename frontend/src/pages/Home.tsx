// Home page — welcome, quick actions, recent documents, system status
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, MessageSquare, FileText, Database, Cpu, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { Header } from '../components/layout/Header';
import { DocumentRow } from '../components/documents/DocumentRow';
import { useDocuments } from '../hooks/useDocuments';
import { useStore } from '../store';
import { statusApi } from '../services/api';

function StatusIndicator({ status }: { status: string }) {
  if (status === 'ok') return <CheckCircle size={14} style={{ color: 'var(--color-success)' }} />;
  if (status === 'warning') return <AlertTriangle size={14} style={{ color: 'var(--color-warning)' }} />;
  return <XCircle size={14} style={{ color: 'var(--color-error)' }} />;
}

export default function Home() {
  const navigate = useNavigate();
  const { documents, isLoading } = useDocuments();
  const { systemStatus, setSystemStatus, setSelectedDocIds, createSession } = useStore();

  useEffect(() => {
    statusApi.get().then(setSystemStatus).catch(() => {});
  }, [setSystemStatus]);

  const handleChatDoc = (docId: string) => {
    setSelectedDocIds([docId]);
    const sid = createSession([docId]);
    navigate('/chat');
  };

  const readyDocs = documents.filter(d => d.status === 'ready');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Header
        title="Retrieval-Based Intelligent QA System for Healthcare Documents"
        subtitle="Grounded question answering across healthcare documents"
      />

      <div className="page-content">
        {/* Welcome */}
        <div className="home-hero">
          <div className="home-hero-copy">
            <span className="eyebrow">Clinical knowledge, clearly connected</span>
            <h2>
              Ask better questions across your healthcare documents.
            </h2>
            <p>
              Upload clinical notes, guidelines, or reports. The system retrieves relevant passages and generates grounded answers — citing exactly where the information came from.
            </p>
          </div>
          <div className="home-hero-actions">
            <button className="btn btn-primary" onClick={() => navigate('/documents')}>
              <Upload size={15} /> Upload document
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/chat')}>
              <MessageSquare size={15} /> New chat
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: 'var(--space-6)', alignItems: 'start' }}>
          {/* Recent documents */}
          <div className="section">
            <div className="section-header">
              <div>
                <div className="section-title">Recent Documents</div>
                <div className="section-subtitle">
                  {readyDocs.length > 0
                    ? `${readyDocs.length} document${readyDocs.length !== 1 ? 's' : ''} indexed`
                    : 'No documents yet'}
                </div>
              </div>
              {documents.length > 0 && (
                <button className="btn btn-ghost btn-sm" onClick={() => navigate('/documents')}>
                  View all
                </button>
              )}
            </div>

            {isLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {[1, 2, 3].map(i => (
                  <div key={i} className="skeleton" style={{ height: 64, borderRadius: 'var(--radius-md)' }} />
                ))}
              </div>
            ) : documents.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--space-8) var(--space-4)' }}>
                <div className="empty-state-icon"><FileText size={22} /></div>
                <div className="empty-state-title">No documents yet</div>
                <div className="empty-state-body">
                  Upload a PDF, DOCX, or TXT file to create your first searchable knowledge source.
                </div>
                <button className="btn btn-primary btn-sm" onClick={() => navigate('/documents')}>
                  <Upload size={14} /> Upload document
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {documents.slice(0, 5).map(doc => (
                  <DocumentRow
                    key={doc.doc_id}
                    doc={doc}
                    onChat={() => handleChatDoc(doc.doc_id)}
                    onClick={() => navigate('/documents')}
                  />
                ))}
              </div>
            )}
          </div>

          {/* System status */}
          <div className="section">
            <div className="section-header">
              <div className="section-title">System Status</div>
            </div>
            <div style={{ background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
              {systemStatus ? (
                <>
                  <div style={{ padding: 'var(--space-3) var(--space-4)', background: 'var(--color-bg-surface-alt)', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <div className={`status-dot ${systemStatus.status === 'healthy' ? 'ok' : systemStatus.status === 'degraded' ? 'warning' : 'error'}`} />
                    <span style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--fw-medium)' as any, color: 'var(--color-text-primary)', textTransform: 'capitalize' }}>
                      {systemStatus.status}
                    </span>
                  </div>
                  {systemStatus.components.map(c => (
                    <div key={c.name} style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-2)', padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--color-border-subtle)' }}>
                      <StatusIndicator status={c.status} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--fw-medium)' as any, color: 'var(--color-text-primary)' }}>{c.name}</div>
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', marginTop: 2 }}>{c.detail}</div>
                      </div>
                    </div>
                  ))}
                  <div style={{ padding: 'var(--space-3) var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>Documents indexed</span>
                      <span style={{ fontWeight: 'var(--fw-semibold)' as any }}>{systemStatus.document_count}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>KB chunks</span>
                      <span style={{ fontWeight: 'var(--fw-semibold)' as any }}>
                        {systemStatus.kb_available ? systemStatus.kb_chunk_count.toLocaleString() : '—'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)' }}>
                      <span style={{ color: 'var(--color-text-secondary)' }}>LLM</span>
                      <span style={{ fontWeight: 'var(--fw-semibold)' as any }}>{systemStatus.llm_provider}/{systemStatus.llm_model}</span>
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ padding: 'var(--space-4)', display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                  <div className="spinner" />
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>Loading status...</span>
                </div>
              )}
            </div>

            {/* Quick links */}
            <div style={{ marginTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate('/evaluation')}>
                <Database size={13} /> View Evaluation
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate('/architecture')}>
                <Cpu size={13} /> System Architecture
              </button>
            </div>
          </div>
        </div>

        {/* Medical notice */}
        <div className="medical-notice" style={{ marginTop: 'var(--space-6)' }}>
          <AlertTriangle size={13} />
          <span>Information generated by this system is for educational reference only. It does not replace professional medical advice, diagnosis, or treatment.</span>
        </div>
      </div>
    </div>
  );
}
