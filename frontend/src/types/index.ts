export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export type StepStatus = "pending" | "running" | "done" | "failed";

export interface ProcessingStep {
  key: string;
  label: string;
  status: StepStatus;
  percent?: number | null;
}

export interface PaperDocument {
  id: string;
  title: string;
  authors: string[];
  affiliations: string[];
  abstract?: string | null;
  keywords: string[];
  year?: number | null;
  doi?: string | null;
  venue?: string | null;
  fileName: string;
  fileSize: number;
  pageCount: number;
  status: DocumentStatus;
  steps: ProcessingStep[];
  error?: string | null;
  createdAt: string;
}

export interface Section {
  id: string;
  documentId: string;
  title: string;
  sectionNumber?: string | null;
  kind: string;
  order: number;
  startPage: number;
  endPage?: number | null;
}

export type ParagraphKind =
  | "paragraph"
  | "heading"
  | "equation"
  | "caption"
  | "list"
  | "reference";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Paragraph {
  id: string;
  documentId: string;
  sectionId: string;
  pageNumber: number;
  originalText: string;
  translatedText?: string | null;
  order: number;
  kind: ParagraphKind;
  boundingBox?: BoundingBox | null;
}

export interface Figure {
  id: string;
  documentId: string;
  sectionId?: string | null;
  pageNumber: number;
  caption: string;
  label?: string | null;
  imageUrl: string;
}

export interface PaperTable {
  id: string;
  documentId: string;
  sectionId?: string | null;
  pageNumber: number;
  caption: string;
  label?: string | null;
  rows: string[][];
}

export interface Citation {
  page: number;
  section: string;
  paragraphId: string;
  snippet?: string | null;
}

export type ContextMode =
  | "entire_document"
  | "current_section"
  | "current_page"
  | "selected_text";

export type ExplanationLevel =
  | "beginner"
  | "undergraduate"
  | "graduate"
  | "researcher";

export type ChatAction = "ask" | "explain" | "translate" | "summarize";

export interface ChatRequest {
  message: string;
  context: ContextMode;
  sectionId?: string;
  page?: number;
  selectedText?: string;
  level?: ExplanationLevel;
  action?: ChatAction;
  sessionId?: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  sessionId: string;
  messageId: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  createdAt: string;
  pending?: boolean;
  error?: boolean;
}

export interface SearchResult {
  paragraphId: string;
  sectionId: string;
  sectionTitle: string;
  page: number;
  preview: string;
  score?: number | null;
}

export interface Note {
  id: string;
  documentId: string;
  paragraphId: string;
  selectedText?: string | null;
  content: string;
  createdAt: string;
}

export interface Highlight {
  id: string;
  documentId: string;
  paragraphId: string;
  selectedText: string;
  startOffset: number;
  endOffset: number;
  color?: string | null;
  createdAt: string;
}

export type SummaryLength = "one_sentence" | "short" | "detailed";

export interface Summary {
  documentId: string;
  length: SummaryLength;
  content: string;
  citations: Citation[];
  createdAt: string;
}

export type ReadingMode = "english" | "chinese" | "bilingual";
