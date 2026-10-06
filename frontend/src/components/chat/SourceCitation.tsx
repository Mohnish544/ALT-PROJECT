// Source citation component — expandable passage viewer
import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Database } from 'lucide-react';
import type { SourceChunk, SourceType } from '../../types';

interface SourceCitationProps {
  sources: SourceChunk[];
  sourceType: SourceType;
}

function SourceBadge({ sourceType }: { sourceType: SourceType }) {
  const configs = {
    document:       { label: 'Document',       cls: 'badge-doc' },
    knowledge_base: { label: 'Medical KB',     cls: 'badge-kb' },
    combined:       { label: 'Combined',       cls: 'badge-combined' },
    none:           { label: 'No Source',      cls: 'badge-default' },
  };
  const c = configs[sourceType] ?? configs.none;
  return <span className={`badge ${c.cls}`}>{c.label}</span>;
}

function SingleSource({ chunk, rank }: { chunk: SourceChunk; rank: number }) {
  const [open, setOpen] = useState(false);

  const Icon = chunk.source_type === 'document' ? FileText : Database;
  const scorePercent = Math.round(chunk.score * 100);

  return (
    <div className="source-citation">
      <div
        className="source-citation-header"
        onClick={() => setOpen(!open)}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setOpen(!open)}
        aria-expanded={open}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flex: 1, minWidth: 0 }}>
          <Icon size={12} style={{ color: 'var(--color-text-tertiary)', flexShrink: 0 }} />
          <span style={{ fontWeight: 'var(--fw-medium)' as any, color: 'var(--color-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            [{rank}] {chunk.display_source || chunk.doc_id}
          </span>
          {chunk.page_hint && (
            <span style={{ color: 'var(--color-text-tertiary)', flexShrink: 0 }}>
              · p.{chunk.page_hint}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
          <span style={{ color: 'var(--color-text-tertiary)' }}>{scorePercent}% match</span>
          {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </div>
      </div>

      {open && (
        <div className="source-citation-body">
          {chunk.text}
        </div>
      )}
    </div>
  );
}

export function SourceCitation({ sources, sourceType }: SourceCitationProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontWeight: 'var(--fw-medium)' as any }}>
          Source
        </span>
        <SourceBadge sourceType={sourceType} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        {sources.slice(0, 3).map((s, i) => (
          <SingleSource key={`${s.doc_id}-${s.chunk_index}`} chunk={s} rank={i + 1} />
        ))}
      </div>
    </div>
  );
}
