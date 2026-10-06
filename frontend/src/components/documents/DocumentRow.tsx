// Document row component — compact list item for document library
import React from 'react';
import { FileText, File, Trash2, MessageSquare, CheckSquare, Square } from 'lucide-react';
import type { Document } from '../../types';

const STATUS_CONFIG = {
  ready:     { label: 'Ready',      cls: 'badge-success' },
  uploading: { label: 'Uploading',  cls: 'badge-info' },
  extracting:{ label: 'Extracting', cls: 'badge-info' },
  cleaning:  { label: 'Cleaning',   cls: 'badge-info' },
  chunking:  { label: 'Chunking',   cls: 'badge-info' },
  embedding: { label: 'Embedding',  cls: 'badge-info' },
  indexing:  { label: 'Indexing',   cls: 'badge-info' },
  error:     { label: 'Error',      cls: 'badge-error' },
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

interface DocumentRowProps {
  doc: Document;
  selected?: boolean;
  onSelect?: () => void;
  onDelete?: () => void;
  onChat?: () => void;
  onClick?: () => void;
}

export function DocumentRow({ doc, selected, onSelect, onDelete, onChat, onClick }: DocumentRowProps) {
  const status = STATUS_CONFIG[doc.status] ?? STATUS_CONFIG.ready;
  const isReady = doc.status === 'ready';
  const isProcessing = !isReady && doc.status !== 'error';

  return (
    <div className="document-row" onClick={onClick} role={onClick ? 'button' : undefined} tabIndex={onClick ? 0 : undefined}>
      {/* Selection checkbox */}
      {onSelect && (
        <button
          className="btn btn-ghost btn-icon"
          onClick={e => { e.stopPropagation(); onSelect(); }}
          aria-label={selected ? 'Deselect document' : 'Select document'}
          style={{ color: selected ? 'var(--color-brand-primary)' : 'var(--color-text-tertiary)' }}
        >
          {selected ? <CheckSquare size={16} /> : <Square size={16} />}
        </button>
      )}

      {/* File icon */}
      <div className="document-row-icon">
        {doc.file_type === 'pdf' ? <FileText size={16} /> : <File size={16} />}
      </div>

      {/* Meta */}
      <div className="document-row-meta">
        <div className="document-row-name">{doc.filename}</div>
        <div className="document-row-info">
          {formatSize(doc.file_size)}
          {doc.page_count > 0 && ` · ${doc.page_count} page${doc.page_count !== 1 ? 's' : ''}`}
          {doc.chunk_count > 0 && ` · ${doc.chunk_count} chunks`}
          {' · '}
          {formatDate(doc.upload_ts)}
          {doc.processing_time_s && ` · indexed in ${doc.processing_time_s.toFixed(1)}s`}
        </div>
      </div>

      {/* Status badge */}
      <span className={`badge ${status.cls}`}>
        {isProcessing && <span className="spinner" style={{ width: 8, height: 8, borderWidth: 1 }} />}
        {status.label}
      </span>

      {/* Actions */}
      <div className="document-row-actions">
        {isReady && onChat && (
          <button
            className="btn btn-ghost btn-icon"
            onClick={e => { e.stopPropagation(); onChat(); }}
            title="Ask questions about this document"
            aria-label="Start chat about document"
          >
            <MessageSquare size={14} />
          </button>
        )}
        {onDelete && (
          <button
            className="btn btn-ghost btn-icon"
            onClick={e => { e.stopPropagation(); onDelete(); }}
            title="Delete document"
            aria-label="Delete document"
            style={{ color: 'var(--color-error)' }}
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
