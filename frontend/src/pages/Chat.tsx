// Chat page — full conversational interface with document context
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Plus, Trash2, FileText, Database, AlertTriangle } from 'lucide-react';
import { Header } from '../components/layout/Header';
import { ChatMessageComponent } from '../components/chat/ChatMessage';
import { useChat } from '../hooks/useChat';
import { useDocuments } from '../hooks/useDocuments';
import { useStore } from '../store';
import { chatApi } from '../services/api';

export default function Chat() {
  const navigate = useNavigate();
  const {
    sessions, activeSessionId, createSession,
    setActiveSession, clearSession,
    selectedDocIds, setSelectedDocIds,
  } = useStore();
  const { documents } = useDocuments();
  const readyDocs = documents.filter(d => d.status === 'ready');

  // Ensure we have an active session
  useEffect(() => {
    if (!activeSessionId || !sessions[activeSessionId]) {
      createSession(selectedDocIds);
    }
  }, []);

  const sessionId = activeSessionId || Object.keys(sessions)[0] || '';
  const session = sessions[sessionId];
  const messages = session?.messages ?? [];

  const { sendMessage, isLoading } = useChat(sessionId);

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || isLoading) return;
    setInput('');
    sendMessage(q);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const handleNewChat = () => {
    createSession(selectedDocIds);
  };

  const sourceLabel = selectedDocIds.length > 0
    ? `${selectedDocIds.length} document${selectedDocIds.length !== 1 ? 's' : ''} selected`
    : 'No documents — using general KB only';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header
        title="Chat"
        subtitle={sourceLabel}
        actions={
          <>
            <button className="btn btn-ghost btn-sm" onClick={handleNewChat} title="New conversation">
              <Plus size={14} /> New
            </button>
            {messages.length > 0 && (
              <button
                className="btn btn-ghost btn-icon"
                onClick={() => clearSession(sessionId)}
                title="Clear conversation"
                aria-label="Clear conversation"
              >
                <Trash2 size={15} />
              </button>
            )}
          </>
        }
      />

      {/* Document context bar */}
      {readyDocs.length > 0 && (
        <div style={{
          background: 'var(--color-bg-surface)',
          borderBottom: '1px solid var(--color-border-subtle)',
          padding: 'var(--space-2) var(--space-6)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
          overflowX: 'auto',
        }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', flexShrink: 0 }}>
            Search in:
          </span>
          <button
            className={`badge ${selectedDocIds.length === 0 ? 'badge-info' : 'badge-default'}`}
            onClick={() => setSelectedDocIds([])}
            style={{ cursor: 'pointer', border: 'none' }}
          >
            <Database size={10} /> All documents + KB
          </button>
          {readyDocs.map(doc => (
            <button
              key={doc.doc_id}
              className={`badge ${selectedDocIds.includes(doc.doc_id) ? 'badge-doc' : 'badge-default'}`}
              onClick={() => {
                setSelectedDocIds(
                  selectedDocIds.includes(doc.doc_id)
                    ? selectedDocIds.filter(id => id !== doc.doc_id)
                    : [...selectedDocIds, doc.doc_id]
                );
              }}
              style={{ cursor: 'pointer', border: 'none', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title={doc.filename}
            >
              <FileText size={10} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {doc.filename.length > 20 ? doc.filename.slice(0, 20) + '…' : doc.filename}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Messages area */}
      <div
        className="page-content no-pad"
        style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}
      >
        {messages.length === 0 ? (
          <div className="empty-state" style={{ marginTop: 'var(--space-12)' }}>
            <div className="empty-state-icon">
              <Database size={22} />
            </div>
            <div className="empty-state-title">Start a conversation</div>
            <div className="empty-state-body">
              {readyDocs.length > 0
                ? 'Ask questions about your documents. The system retrieves relevant passages and generates grounded, cited answers.'
                : 'No documents indexed yet. Upload a document to ask document-specific questions, or ask general medical questions using the knowledge base.'}
            </div>
            {readyDocs.length === 0 && (
              <button className="btn btn-primary btn-sm" onClick={() => navigate('/documents')}>
                Upload a document
              </button>
            )}
            {/* Suggested questions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', width: '100%', maxWidth: 480, marginTop: 'var(--space-2)' }}>
              {[
                'What medications are listed in the document?',
                'What is the patient\'s diagnosis?',
                'What are the symptoms of hypertension?',
              ].map(q => (
                <button
                  key={q}
                  className="btn btn-secondary btn-sm"
                  onClick={() => sendMessage(q)}
                  style={{ textAlign: 'left', justifyContent: 'flex-start' }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <ChatMessageComponent key={msg.id} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Ask a question about your documents or medical topics..."
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
            aria-label="Chat input"
          />
          <button
            className="btn btn-primary btn-icon"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
          >
            {isLoading ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <Send size={15} />}
          </button>
        </div>
        <div style={{ maxWidth: 'var(--chat-max-w)', margin: '0 auto', marginTop: 'var(--space-2)' }}>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', textAlign: 'center' }}>
            Press Enter to send · Shift+Enter for new line · Answers are for reference only
          </p>
        </div>
      </div>
    </div>
  );
}
