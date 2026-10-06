// Retrieval details expandable section for transparency
import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { RetrievalInfo } from '../../types';

interface RetrievalDetailsProps {
  info: RetrievalInfo;
}

export function RetrievalDetails({ info }: RetrievalDetailsProps) {
  const [open, setOpen] = useState(false);

  const rows = [
    { key: 'Strategy',       val: info.strategy },
    { key: 'Source',         val: info.source_type },
    { key: 'Fallback used',  val: info.fallback_triggered ? 'Yes' : 'No' },
    { key: 'Doc score',      val: `${(info.doc_max_score * 100).toFixed(1)}%` },
    { key: 'KB score',       val: `${(info.kb_max_score * 100).toFixed(1)}%` },
    { key: 'Chunks used',    val: String(info.num_chunks_retrieved) },
  ];

  return (
    <div className="retrieval-details">
      <div
        className="retrieval-details-toggle"
        onClick={() => setOpen(!open)}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setOpen(!open)}
        aria-expanded={open}
      >
        <span>How this answer was generated</span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </div>

      {open && (
        <div className="retrieval-details-body">
          {rows.map(r => (
            <div key={r.key} className="retrieval-detail-row">
              <span className="retrieval-detail-key">{r.key}</span>
              <span className="retrieval-detail-val">{r.val}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
