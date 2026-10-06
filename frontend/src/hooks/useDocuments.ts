// useDocuments hook — loads and manages document list
import { useState, useCallback, useEffect } from 'react';
import { documentsApi, ApiError } from '../services/api';
import { useStore } from '../store';

export function useDocuments() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { documents, setDocuments, addDocument, removeDocument, addToast } = useStore();

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await documentsApi.list();
      setDocuments(res.documents);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load documents.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [setDocuments]);

  const deleteDoc = useCallback(async (docId: string) => {
    try {
      await documentsApi.delete(docId);
      removeDocument(docId);
      addToast({ type: 'success', title: 'Document removed' });
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to delete document.';
      addToast({ type: 'error', title: 'Delete failed', message: msg });
    }
  }, [removeDocument, addToast]);

  useEffect(() => { load(); }, [load]);

  return { documents, isLoading, error, reload: load, deleteDoc };
}
