// Architecture page — visual pipeline explanation for academic demo
import React from 'react';
import { Upload, FileSearch, Scissors, Cpu, Database, Search, MessageSquare, BookOpen, ArrowDown } from 'lucide-react';
import { Header } from '../components/layout/Header';

interface StepProps {
  icon: React.ReactNode;
  label: string;
  desc: string;
  detail: string;
}

function PipelineStep({ icon, label, desc, detail }: StepProps) {
  return (
    <div className="pipeline-step">
      <div className="pipeline-box">
        <div className="pipeline-box-icon">{icon}</div>
        <div className="pipeline-box-text">
          <div className="pipeline-box-label">{label}</div>
          <div className="pipeline-box-desc">{desc}</div>
        </div>
      </div>
      {detail && (
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: 4, maxWidth: 320, textAlign: 'center' }}>
          {detail}
        </div>
      )}
      <div className="pipeline-arrow"><ArrowDown size={14} /></div>
    </div>
  );
}

const UPLOAD_STEPS: StepProps[] = [
  { icon: <Upload size={16} />,     label: 'Upload',     desc: 'PDF / DOCX / TXT',           detail: 'Accepts up to 50 MB; multi-column PDF handled via pdfplumber' },
  { icon: <FileSearch size={16} />, label: 'Extract',    desc: 'Raw text extraction',         detail: 'pdfplumber (primary) → pypdf fallback; table text preserved' },
  { icon: <BookOpen size={16} />,   label: 'Preprocess', desc: 'Clean, normalise, lemmatise', detail: 'Unicode normalisation, medical abbreviation expansion, NLTK lemmatiser' },
  { icon: <Scissors size={16} />,   label: 'Chunk',      desc: 'Sliding window passages',     detail: '400 token chunks with 50 token overlap; sentence-boundary-aware' },
  { icon: <Cpu size={16} />,        label: 'Embed',      desc: 'Dense vector encoding',       detail: 'pritamdeka/S-PubMedBert-MS-MARCO — 768-dim biomedical embeddings' },
  { icon: <Database size={16} />,   label: 'Index',      desc: 'FAISS IndexFlatIP',           detail: 'L2-normalised vectors; cosine similarity via inner product; persisted to disk' },
];

const QUERY_STEPS: StepProps[] = [
  { icon: <MessageSquare size={16} />, label: 'Question',  desc: 'User natural-language query', detail: 'Conversation history maintained across turns' },
  { icon: <Cpu size={16} />,           label: 'Encode',    desc: 'Query embedding',             detail: 'Same model as document chunks for compatible vector space' },
  { icon: <Search size={16} />,        label: 'Retrieve',  desc: 'Hybrid retrieval',            detail: 'Doc index first (top-5); fallback to KB if max score < 0.35' },
  { icon: <BookOpen size={16} />,      label: 'Generate',  desc: 'LLM answer synthesis',        detail: 'GPT-4o-mini / Claude / Ollama / Mock — pluggable via .env' },
  { icon: <Database size={16} />,      label: 'Cite',      desc: 'Source attribution',          detail: 'Each passage tagged: document | knowledge_base | combined' },
];

export default function Architecture() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Header title="How It Works" subtitle="MedLens RAG pipeline — from upload to cited answer" />

      <div className="page-content">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-8)', alignItems: 'start' }}>

          {/* Indexing pipeline */}
          <div>
            <div className="section-header" style={{ marginBottom: 'var(--space-5)' }}>
              <div>
                <div className="section-title">Document Indexing Pipeline</div>
                <div className="section-subtitle">Runs once when a document is uploaded</div>
              </div>
            </div>
            <div className="pipeline-diagram">
              {UPLOAD_STEPS.map((s, i) => (
                <PipelineStep key={i} {...s} />
              ))}
              <div className="pipeline-box" style={{ borderColor: 'var(--color-success)', background: 'var(--color-success-bg)' }}>
                <div className="pipeline-box-icon" style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}>
                  <Database size={16} />
                </div>
                <div className="pipeline-box-text">
                  <div className="pipeline-box-label" style={{ color: 'var(--color-success)' }}>Ready</div>
                  <div className="pipeline-box-desc">Searchable document index</div>
                </div>
              </div>
            </div>
          </div>

          {/* Query pipeline */}
          <div>
            <div className="section-header" style={{ marginBottom: 'var(--space-5)' }}>
              <div>
                <div className="section-title">Query & Answer Pipeline</div>
                <div className="section-subtitle">Runs on every user question</div>
              </div>
            </div>
            <div className="pipeline-diagram">
              {QUERY_STEPS.map((s, i) => (
                <PipelineStep key={i} {...s} />
              ))}
              <div className="pipeline-box" style={{ borderColor: 'var(--color-brand-primary)', background: 'var(--color-brand-light)' }}>
                <div className="pipeline-box-icon">
                  <MessageSquare size={16} />
                </div>
                <div className="pipeline-box-text">
                  <div className="pipeline-box-label" style={{ color: 'var(--color-brand-primary)' }}>Answer</div>
                  <div className="pipeline-box-desc">Grounded, cited response</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Hybrid retrieval explanation */}
        <div style={{ marginTop: 'var(--space-8)', background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
          <div style={{ padding: 'var(--space-4) var(--space-5)', background: 'var(--color-bg-surface-alt)', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div className="section-title">Hybrid Retrieval Logic</div>
            <div className="section-subtitle">How MedLens decides between document and knowledge base</div>
          </div>
          <div style={{ padding: 'var(--space-5)', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-4)' }}>
            {[
              { title: 'Document Answer', condition: 'Max similarity ≥ 0.35', desc: 'Top-k chunks are retrieved from the uploaded document index and passed to the LLM.', badge: 'badge-doc', label: 'Document' },
              { title: 'Combined Answer', condition: '0.25 ≤ similarity < 0.35', desc: 'Moderate confidence. Chunks from both the document and knowledge base are combined for broader context.', badge: 'badge-combined', label: 'Combined' },
              { title: 'KB Fallback', condition: 'Max similarity < 0.25', desc: 'The question goes beyond the document. The system retrieves from the MedQuAD knowledge base instead.', badge: 'badge-kb', label: 'Medical KB' },
            ].map(c => (
              <div key={c.title} style={{ padding: 'var(--space-4)', background: 'var(--color-bg-base)', borderRadius: 'var(--radius-md)' }}>
                <span className={`badge ${c.badge}`} style={{ marginBottom: 'var(--space-2)', display: 'inline-flex' }}>{c.label}</span>
                <div style={{ fontWeight: 'var(--fw-semibold)' as any, fontSize: 'var(--text-sm)', color: 'var(--color-text-primary)', marginBottom: 'var(--space-1)' }}>{c.title}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', marginBottom: 'var(--space-2)' }}>{c.condition}</div>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--lh-relaxed)' }}>{c.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Tech stack */}
        <div style={{ marginTop: 'var(--space-6)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-3)' }}>
          {[
            { layer: 'NLP / Preprocessing', tech: 'NLTK, spaCy, scikit-learn' },
            { layer: 'Embeddings', tech: 'sentence-transformers, PubMedBERT' },
            { layer: 'Vector Search', tech: 'FAISS IndexFlatIP' },
            { layer: 'Baseline Retrieval', tech: 'TF-IDF (sklearn), BM25' },
            { layer: 'LLM', tech: 'OpenAI / Anthropic / Ollama' },
            { layer: 'Backend', tech: 'FastAPI, Pydantic, uvicorn' },
            { layer: 'Frontend', tech: 'React, Vite, TypeScript, Zustand' },
            { layer: 'Knowledge Base', tech: 'MedQuAD (Apache 2.0)' },
          ].map(t => (
            <div key={t.layer} style={{ padding: 'var(--space-3) var(--space-4)', background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginBottom: 2 }}>{t.layer}</div>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--fw-medium)' as any, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>{t.tech}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
