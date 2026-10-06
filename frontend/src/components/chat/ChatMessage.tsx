// Chat message component with markdown rendering
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Activity } from 'lucide-react';
import { SourceCitation } from './SourceCitation';
import { RetrievalDetails } from './RetrievalDetails';
import type { ChatMessage as ChatMessageType } from '../../types';

function LoadingDots() {
  return (
    <div style={{ display: 'flex', gap: 4, padding: '4px 0', alignItems: 'center' }}>
      {['Searching documents', 'Comparing passages', 'Generating response'].map((step, i) => (
        <span
          key={i}
          style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--color-text-secondary)',
            animation: `skeleton-pulse 1.4s ${i * 0.2}s ease-in-out infinite`,
          }}
        >
          {step}
          {i < 2 && <span style={{ margin: '0 4px', opacity: 0.5 }}>→</span>}
        </span>
      ))}
    </div>
  );
}

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessageComponent({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`chat-message ${message.role}`}>
      {/* Avatar + timestamp row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 24,
          height: 24,
          borderRadius: '50%',
          background: isUser ? 'var(--color-brand-primary)' : 'var(--color-bg-surface-alt)',
          border: '1px solid var(--color-border)',
          color: isUser ? 'white' : 'var(--color-text-secondary)',
          flexShrink: 0,
        }}>
          {isUser ? <User size={12} /> : <Activity size={12} />}
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)' }}>
          {isUser ? 'You' : 'MedLens'}
          {' · '}
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {/* Message bubble */}
      <div className={`chat-bubble ${message.role}`}>
        {message.is_loading ? (
          <LoadingDots />
        ) : isUser ? (
          <span>{message.content}</span>
        ) : (
          <div className="prose">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {/* Sources and retrieval details for assistant messages */}
      {!isUser && !message.is_loading && message.sources && message.sources.length > 0 && (
        <div style={{ maxWidth: '100%' }}>
          <SourceCitation sources={message.sources} sourceType={message.source_type ?? 'none'} />
          {message.retrieval_info && (
            <div style={{ marginTop: 'var(--space-2)' }}>
              <RetrievalDetails info={message.retrieval_info} />
            </div>
          )}
        </div>
      )}

      {/* Medical safety notice for assistant answers */}
      {!isUser && !message.is_loading && message.content && !message.error && (
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: 'var(--space-1)' }}>
          ⚕ For educational reference only — not medical advice.
        </div>
      )}
    </div>
  );
}
