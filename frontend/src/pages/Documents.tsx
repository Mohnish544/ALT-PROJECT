// Documents page — library with upload, document management, and selection for chat
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, MessageSquare, RefreshCw, Trash2 } from 'lucide-react';
import { Header } from '../components/layout/Header';
import { DocumentRow } from '../components/documents/DocumentRow';
import { FileUpload } from '../components/documents/FileUpload';
import { useDocuments } from '../hooks/useDocuments';
import { useStore } from '../store';

export default function Documents() {
  const navigate = useNavigate();
  const { documents, isLoading, error, reload, deleteDoc } = useDocuments();
  const { selectedDocIds, toggleDocSelection, setSelectedDocIds, createSession } = useStore();
  const [showUpload, setShowUpload] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleChatWithSelected = () => {
    const sid = createSession(selectedDocIds);
    navigate('/chat');
  };

  const handleDelete = async (docId: string) => {
    await deleteDoc(docId);
    setConfirmDelete(null);
    // Remove from selection if selected
    if (selectedDocIds.includes(docId)) {
      setSelectedDocIds(selectedDocIds.filter(id => id !== docId));
    }
  };

  const readyDocs = documents.filter(d => d.status === 'ready');
  const processingDocs = documents.filter(d => d.status !== 'ready' && d.status !== 'error');
  const errorDocs = documents.filter(d => d.status === 'error');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Header
        title="Documents"
        subtitle={`${readyDocs.length} ready · ${documents.length} total`}
        actions={
          <>
            {selectedDocIds.length > 0 && (
              <button className="btn btn-primary btn-sm" onClick={handleChatWithSelected}>
                <MessageSquare size={14} />
                Chat with {selectedDocIds.length} selected
              </button>
            )}
            <button className="btn btn-ghost btn-icon" onClick={reload} title="Refresh" aria-label="Refresh document list">
              <RefreshCw size={16} />
            </button>
            <button className="btn btn-primary" onClick={() => setShowUpload(!showUpload)}>
              <Upload size={15} />
              {showUpload ? 'Hide upload' : 'Upload document'}
            </button>
          </>
        }
      />

      <div className="page-content">
        {/* Upload area */}
        {showUpload && (
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <FileUpload onComplete={() => { reload(); }} />
          </div>
        )}

        {/* Error state */}
        {error && (
          <div style={{ padding: 'var(--space-4)', background: 'var(--color-error-bg)', border: '1px solid var(--color-error-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-error)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)' }}>
            Failed to load documents: {error}
            <button className="btn btn-sm" onClick={reload} style={{ marginLeft: 'var(--space-3)' }}>Retry</button>
          </div>
        )}

        {/* Processing documents */}
        {processingDocs.length > 0 && (
          <div className="section">
            <div className="section-title" style={{ marginBottom: 'var(--space-3)' }}>Processing</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {processingDocs.map(doc => (
                <DocumentRow key={doc.doc_id} doc={doc} />
              ))}
            </div>
          </div>
        )}

        {/* Ready documents */}
        <div className="section">
          <div className="section-header">
            <div>
              <div className="section-title">Indexed Documents</div>
              {selectedDocIds.length > 0 && (
                <div className="section-subtitle">{selectedDocIds.length} selected for chat</div>
              )}
            </div>
            {selectedDocIds.length > 0 && (
              <button className="btn btn-ghost btn-sm" onClick={() => setSelectedDocIds([])}>
                Clear selection
              </button>
            )}
          </div>

          {isLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 64, borderRadius: 'var(--radius-md)' }} />)}
            </div>
          ) : readyDocs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon" style={{ width: 40, height: 40 }}>
                <Upload size={18} />
              </div>
              <div className="empty-state-title">Your document library is empty</div>
              <div className="empty-state-body">
                Upload a PDF, DOCX, or TXT healthcare document to create your first searchable knowledge source.
              </div>
              <button className="btn btn-primary btn-sm" onClick={() => setShowUpload(true)}>
                <Upload size={14} /> Upload document
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {readyDocs.map(doc => (
                <DocumentRow
                  key={doc.doc_id}
                  doc={doc}
                  selected={selectedDocIds.includes(doc.doc_id)}
                  onSelect={() => toggleDocSelection(doc.doc_id)}
                  onDelete={() => setConfirmDelete(doc.doc_id)}
                  onChat={() => {
                    setSelectedDocIds([doc.doc_id]);
                    navigate('/chat');
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Error documents */}
        {errorDocs.length > 0 && (
          <div className="section">
            <div className="section-title" style={{ marginBottom: 'var(--space-3)', color: 'var(--color-error)' }}>Failed</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {errorDocs.map(doc => (
                <DocumentRow
                  key={doc.doc_id}
                  doc={doc}
                  onDelete={() => deleteDoc(doc.doc_id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="modal-overlay" onClick={() => setConfirmDelete(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Remove document?</span>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--lh-relaxed)' }}>
                This will permanently remove the document and its index. Any chat sessions using it will lose document context.
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setConfirmDelete(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={() => handleDelete(confirmDelete)}>
                <Trash2 size={14} /> Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
