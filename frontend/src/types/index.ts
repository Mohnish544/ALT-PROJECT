// MedLens — TypeScript type definitions
// All shared types used across components, services, and store.

export interface Document {
  doc_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  upload_ts: string;
  status: 'uploading' | 'extracting' | 'cleaning' | 'chunking' | 'embedding' | 'indexing' | 'ready' | 'error';
  processing_time_s?: number;
}

export interface ProcessingStage {
  stage: string;
  status: 'pending' | 'running' | 'done' | 'error';
  message: string;
  duration_s?: number;
}

export interface ProcessingJob {
  doc_id: string;
  filename: string;
  stages: ProcessingStage[];
  status: 'processing' | 'ready' | 'error';
  page_count: number;
  chunk_count: number;
  processing_time_s?: number;
  error?: string;
}

export interface SourceChunk {
  chunk_index: number;
  text: string;
  score: number;
  doc_id: string;
  source_type: 'document' | 'knowledge_base';
  page_hint?: number;
  display_source: string;
}

export interface RetrievalInfo {
  query: string;
  source_type: SourceType;
  fallback_triggered: boolean;
  doc_max_score: number;
  kb_max_score: number;
  num_chunks_retrieved: number;
  strategy: string;
}

export type SourceType = 'document' | 'knowledge_base' | 'combined' | 'none';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  source_type?: SourceType;
  sources?: SourceChunk[];
  retrieval_info?: RetrievalInfo;
  provider?: string;
  model?: string;
  error?: string;
  is_loading?: boolean;
}

export interface ChatSession {
  session_id: string;
  messages: ChatMessage[];
  created_at: string;
  doc_ids?: string[];
}

export interface ComponentStatus {
  name: string;
  status: 'ok' | 'warning' | 'error' | 'unavailable';
  detail: string;
}

export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'error';
  components: ComponentStatus[];
  document_count: number;
  kb_available: boolean;
  kb_chunk_count: number;
  embedding_model: string;
  llm_provider: string;
  llm_model: string;
}

export interface MetricResult {
  metric: string;
  semantic_value: number;
  baseline_value: number;
  improvement_pct: number;
}

export interface EvaluationResult {
  metrics: MetricResult[];
  total_questions: number;
  evaluation_timestamp: string;
  notes: string;
}

export interface AppSettings {
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  doc_fallback_threshold: number;
  llm_provider: string;
  llm_model: string;
  kb_available: boolean;
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
}
