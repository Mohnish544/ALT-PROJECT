// Toast notification container
import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useStore } from '../../store';
import type { Toast } from '../../types';

function ToastItem({ toast }: { toast: Toast }) {
  const { removeToast } = useStore();

  const icons = {
    success: <CheckCircle size={16} style={{ color: 'var(--color-success)' }} />,
    error:   <XCircle    size={16} style={{ color: 'var(--color-error)' }} />,
    warning: <AlertTriangle size={16} style={{ color: 'var(--color-warning)' }} />,
    info:    <Info       size={16} style={{ color: 'var(--color-info)' }} />,
  };

  return (
    <div className={`toast ${toast.type}`} role="alert">
      {icons[toast.type]}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 'var(--fw-semibold)' as any, color: 'var(--color-text-primary)', fontSize: 'var(--text-sm)' }}>
          {toast.title}
        </div>
        {toast.message && (
          <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-xs)', marginTop: 2 }}>
            {toast.message}
          </div>
        )}
      </div>
      <button
        className="btn btn-ghost btn-icon"
        onClick={() => removeToast(toast.id)}
        aria-label="Dismiss notification"
        style={{ padding: 4 }}
      >
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts } = useStore();

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map(t => <ToastItem key={t.id} toast={t} />)}
    </div>
  );
}
