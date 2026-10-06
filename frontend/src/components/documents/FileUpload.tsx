// File upload zone — drag & drop + click
import React, { useState, useRef, useCallback } from 'react';
import { Upload, CheckCircle, XCircle, FileText } from 'lucide-react';
import { documentsApi, ApiError } from '../../services/api';
import { useStore } from '../../store';
import type { ProcessingStage } from '../../types';

const ACCEPTED = ['.pdf', '.docx', '.txt'];
const ACCEPTED_MIME = ['application/pdf', 'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

const STAGE_LABELS: Record<string, string> = {
  uploading:  'Saving file',
  extracting: 'Extracting text',
  cleaning:   'Cleaning & normalising',
  chunking:   'Creating searchable passages',
  embedding:  'Generating embeddings',
  indexing:   'Building semantic index',
  ready:      'Ready for queries',
};

interface FileUploadProps {
  onComplete?: () => void;
}

export function FileUpload({ onComplete }: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [stages, setStages] = useState<ProcessingStage[]>([]);
  const [result, setResult] = useState<'success' | 'error' | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const { addDocument, updateDocument, addToast } = useStore();

  const processFile = useCallback(async (file: File) => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      addToast({ type: 'error', title: 'Unsupported file type', message: `Accepted: ${ACCEPTED.join(', ')}` });
      return;
    }

    setUploading(true);
    setStages([]);
    setResult(null);
    setErrorMsg('');

    try {
      const job = await documentsApi.upload(file);

      setStages(job.stages);

      if (job.status === 'ready') {
        setResult('success');
        // Add to store as a Document record
        addDocument({
          doc_id: job.doc_id,
          filename: job.filename,
          file_type: file.name.split('.').pop() ?? 'txt',
          file_size: file.size,
          page_count: job.page_count,
          chunk_count: job.chunk_count,
          upload_ts: new Date().toISOString(),
          status: 'ready',
          processing_time_s: job.processing_time_s,
        });
        addToast({ type: 'success', title: 'Document indexed', message: `${file.name} is ready for queries` });
        onComplete?.();
      } else {
        setResult('error');
        setErrorMsg(job.error ?? 'Processing failed');
        addToast({ type: 'error', title: 'Processing failed', message: job.error });
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Upload failed. Please try again.';
      setResult('error');
      setErrorMsg(msg);
      addToast({ type: 'error', title: 'Upload failed', message: msg });
    } finally {
      setUploading(false);
    }
  }, [addDocument, addToast, onComplete]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }, [processFile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const reset = () => {
    setStages([]);
    setResult(null);
    setErrorMsg('');
    if (fileRef.current) fileRef.current.value = '';
  };

  // Show processing stages
  if (uploading || stages.length > 0) {
    return (
      <div style={{ background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-5)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
          {result === 'success' ? (
            <CheckCircle size={20} style={{ color: 'var(--color-success)' }} />
          ) : result === 'error' ? (
            <XCircle size={20} style={{ color: 'var(--color-error)' }} />
          ) : (
            <div className="spinner" />
          )}
          <span style={{ fontWeight: 'var(--fw-semibold)' as any, fontSize: 'var(--text-sm)', color: 'var(--color-text-primary)' }}>
            {result === 'success' ? 'Document ready'
              : result === 'error' ? 'Processing failed'
              : 'Processing document...'}
          </span>
        </div>

        <div className="stage-list">
          {stages.map((s) => (
            <div key={s.stage} className={`stage-item ${s.status}`}>
              <div className="stage-icon">
                {s.status === 'done' && <CheckCircle size={14} />}
                {s.status === 'error' && <XCircle size={14} />}
                {s.status === 'running' && <div className="spinner" />}
              </div>
              <div>
                <div>{STAGE_LABELS[s.stage] ?? s.stage}</div>
                {s.message && <div className="stage-message">{s.message}</div>}
              </div>
            </div>
          ))}
        </div>

        {(result === 'success' || result === 'error') && (
          <button className="btn btn-secondary btn-sm" onClick={reset} style={{ marginTop: 'var(--space-4)' }}>
            Upload another
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        className={`upload-zone${dragOver ? ' drag-over' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
        aria-label="Upload healthcare document"
      >
        <div className="upload-zone-icon">
          <Upload size={22} />
        </div>
        <div>
          <div className="upload-zone-title">Drop a healthcare document here</div>
          <div className="upload-zone-subtitle">
            or click to browse · Accepts PDF, DOCX, TXT · Max 50 MB
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          {ACCEPTED.map(ext => (
            <span key={ext} className="badge badge-default">{ext.toUpperCase()}</span>
          ))}
        </div>
      </div>
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPTED.join(',')}
        onChange={handleChange}
        style={{ display: 'none' }}
        aria-hidden="true"
      />
    </div>
  );
}
