// useChat hook — manages sending messages and streaming state
import { useState, useCallback } from 'react';
import { chatApi, ApiError } from '../services/api';
import { useStore } from '../store';
import type { ChatMessage } from '../types';

function genId(): string {
  try { return crypto.randomUUID(); } catch { return Math.random().toString(36).slice(2); }
}

export function useChat(sessionId: string) {
  const [isLoading, setIsLoading] = useState(false);
  const { addMessage, updateMessage, addToast, selectedDocIds } = useStore();

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;

    // Add user message immediately
    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content: question.trim(),
      timestamp: new Date().toISOString(),
    };
    addMessage(sessionId, userMsg);

    // Add placeholder assistant message
    const assistantId = genId();
    const loadingMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      is_loading: true,
    };
    addMessage(sessionId, loadingMsg);
    setIsLoading(true);

    try {
      const response = await chatApi.ask({
        question: question.trim(),
        session_id: sessionId,
        doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      });

      updateMessage(sessionId, assistantId, {
        content: response.answer,
        source_type: response.source_type,
        sources: response.sources,
        retrieval_info: response.retrieval_info,
        provider: response.provider,
        model: response.model,
        error: response.error,
        is_loading: false,
      });
    } catch (err) {
      const message = err instanceof ApiError
        ? err.message
        : 'Failed to get a response. Please try again.';

      updateMessage(sessionId, assistantId, {
        content: message,
        is_loading: false,
        error: message,
      });

      addToast({ type: 'error', title: 'Request failed', message });
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading, selectedDocIds, addMessage, updateMessage, addToast]);

  return { sendMessage, isLoading };
}
