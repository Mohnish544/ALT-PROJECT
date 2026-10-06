// Evaluation page — metrics comparison between semantic and TF-IDF retrieval
import React, { useState, useEffect } from 'react';
import { BarChart2, RefreshCw, Info } from 'lucide-react';
import { Header } from '../components/layout/Header';
import { evaluationApi, ApiError } from '../services/api';
import type { EvaluationResult } from '../types';

function MetricBar({ value, max = 1, color }: { value: number; max?: number; color: string }) {
  return (
    <div className="metric-bar">
      <div
        className="metric-bar-fill"
        style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color }}
      />
    </div>
  );
}

export default function Evaluation() {
  const [results, setResults] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runEval = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await evaluationApi.run();
      setResults(res);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Evaluation failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Header
        title="Evaluation"
        subtitle="Retrieval quality metrics: Semantic vs. TF-IDF baseline"
        actions={
          <button className="btn btn-primary btn-sm" onClick={runEval} disabled={loading}>
            {loading ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <RefreshCw size={14} />}
            {loading ? 'Evaluating...' : 'Run evaluation'}
          </button>
        }
      />

      <div className="page-content">
        {/* Info panel */}
        <div style={{ background: 'var(--color-info-bg)', border: '1px solid var(--color-info-border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)', marginBottom: 'var(--space-6)', display: 'flex', gap: 'var(--space-3)' }}>
          <Info size={16} style={{ color: 'var(--color-info)', flexShrink: 0, marginTop: 2 }} />
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--lh-relaxed)' }}>
            Evaluation compares two retrieval strategies on {results?.total_questions ?? 15} held-out Q&A pairs from the sample documents.
            <strong style={{ color: 'var(--color-text-primary)' }}> Semantic retrieval</strong> uses a biomedical sentence-transformer (PubMedBERT-based) for dense vector search.
            <strong style={{ color: 'var(--color-text-primary)' }}> Baseline</strong> uses TF-IDF with bigram features — a standard sparse retrieval method from NLP coursework.
          </div>
        </div>

        {error && (
          <div style={{ padding: 'var(--space-4)', background: 'var(--color-error-bg)', border: '1px solid var(--color-error-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-error)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-4)' }}>
            {error}
          </div>
        )}

        {!results && !loading && !error && (
          <div className="empty-state">
            <div className="empty-state-icon"><BarChart2 size={22} /></div>
            <div className="empty-state-title">No evaluation results yet</div>
            <div className="empty-state-body">
              Click "Run evaluation" to compare semantic retrieval vs. TF-IDF baseline on the held-out question set.
            </div>
            <button className="btn btn-primary" onClick={runEval}>
              <RefreshCw size={14} /> Run evaluation
            </button>
          </div>
        )}

        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="skeleton" style={{ height: 56, borderRadius: 'var(--radius-md)' }} />
            ))}
          </div>
        )}

        {results && !loading && (
          <>
            {/* Legend */}
            <div style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-4)', fontSize: 'var(--text-xs)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <div style={{ width: 12, height: 4, background: 'var(--color-brand-primary)', borderRadius: 2 }} />
                <span style={{ color: 'var(--color-text-secondary)' }}>Semantic (Embedding)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <div style={{ width: 12, height: 4, background: 'var(--color-text-tertiary)', borderRadius: 2 }} />
                <span style={{ color: 'var(--color-text-secondary)' }}>Baseline (TF-IDF)</span>
              </div>
            </div>

            {/* Metrics table */}
            <table className="eval-table" style={{ marginBottom: 'var(--space-6)' }}>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Semantic</th>
                  <th style={{ width: 200 }}>Comparison</th>
                  <th>Baseline</th>
                  <th>Δ Improvement</th>
                </tr>
              </thead>
              <tbody>
                {results.metrics.map(m => (
                  <tr key={m.metric}>
                    <td style={{ fontWeight: 'var(--fw-medium)' as any, color: 'var(--color-text-primary)' }}>
                      {m.metric}
                    </td>
                    <td>
                      <span style={{ fontWeight: 'var(--fw-semibold)' as any, color: 'var(--color-brand-primary)' }}>
                        {(m.semantic_value * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <MetricBar value={m.semantic_value} color="var(--color-brand-primary)" />
                        <MetricBar value={m.baseline_value} color="var(--color-text-tertiary)" />
                      </div>
                    </td>
                    <td style={{ color: 'var(--color-text-secondary)' }}>
                      {(m.baseline_value * 100).toFixed(1)}%
                    </td>
                    <td>
                      <span className={`badge ${m.improvement_pct >= 0 ? 'badge-success' : 'badge-error'}`}>
                        {m.improvement_pct >= 0 ? '+' : ''}{m.improvement_pct.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Notes */}
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 'var(--lh-relaxed)', padding: 'var(--space-3) var(--space-4)', background: 'var(--color-bg-surface-alt)', borderRadius: 'var(--radius-md)' }}>
              <strong>Notes:</strong> {results.notes}
              <br />
              Evaluated: {new Date(results.evaluation_timestamp).toLocaleString()}
              {' · '}
              {results.total_questions} questions
            </div>
          </>
        )}
      </div>
    </div>
  );
}
