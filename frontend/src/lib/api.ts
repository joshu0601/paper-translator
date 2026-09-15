import type {
  ChatRequest,
  ChatResponse,
  Figure,
  Highlight,
  Note,
  PageInfo,
  PaperDocument,
  PaperTable,
  Paragraph,
  SearchResult,
  Section,
  Summary,
  SummaryLength,
} from "@/types";

/**
 * Backend base URL. Explicit `NEXT_PUBLIC_API_BASE_URL` wins; otherwise the
 * backend is assumed to run on port 8000 of the host that served this page,
 * which also works for other devices on the LAN (they open
 * http://<your-ip>:3000 and reach http://<your-ip>:8000).
 */
function resolveApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

export function apiBase(): string {
  return resolveApiBase();
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function fileUrl(documentId: string) {
  return `${apiBase()}/api/documents/${documentId}/file`;
}

export function translatedPdfUrl(documentId: string) {
  return `${apiBase()}/api/documents/${documentId}/translated.pdf`;
}

export function absoluteUrl(path: string) {
  return path.startsWith("http") ? path : `${apiBase()}${path}`;
}

export const api = {
  listDocuments: () => request<PaperDocument[]>("/api/documents"),
  getDocument: (id: string) => request<PaperDocument>(`/api/documents/${id}`),
  deleteDocument: (id: string) =>
    request<void>(`/api/documents/${id}`, { method: "DELETE" }),
  updateDocument: (id: string, patch: Partial<PaperDocument>) =>
    request<PaperDocument>(`/api/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<PaperDocument>("/api/documents/upload", {
      method: "POST",
      body: form,
    });
  },
  createDemoDocument: () =>
    request<PaperDocument>("/api/documents/demo", { method: "POST" }),
  reprocess: (id: string) =>
    request<PaperDocument>(`/api/documents/${id}/process`, { method: "POST" }),
  relayout: (id: string) =>
    request<PaperDocument>(`/api/documents/${id}/layout`, { method: "POST" }),
  translate: (id: string) =>
    request<PaperDocument>(`/api/documents/${id}/translate`, {
      method: "POST",
    }),
  getPages: (id: string) => request<PageInfo[]>(`/api/documents/${id}/pages`),
  getSections: (id: string) => request<Section[]>(`/api/documents/${id}/sections`),
  getParagraphs: (id: string) =>
    request<Paragraph[]>(`/api/documents/${id}/paragraphs`),
  getFigures: (id: string) => request<Figure[]>(`/api/documents/${id}/figures`),
  getTables: (id: string) => request<PaperTable[]>(`/api/documents/${id}/tables`),
  chat: (id: string, body: ChatRequest) =>
    request<ChatResponse>(`/api/documents/${id}/chat`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  search: (id: string, query: string, type: "exact" | "semantic") =>
    request<SearchResult[]>(`/api/documents/${id}/search`, {
      method: "POST",
      body: JSON.stringify({ query, type }),
    }),
  getNotes: (id: string) => request<Note[]>(`/api/documents/${id}/notes`),
  createNote: (
    id: string,
    body: { paragraphId: string; content: string; selectedText?: string },
  ) =>
    request<Note>(`/api/documents/${id}/notes`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteNote: (noteId: string) =>
    request<void>(`/api/notes/${noteId}`, { method: "DELETE" }),
  getHighlights: (id: string) =>
    request<Highlight[]>(`/api/documents/${id}/highlights`),
  createHighlight: (
    id: string,
    body: {
      paragraphId: string;
      selectedText: string;
      startOffset: number;
      endOffset: number;
      color?: string;
    },
  ) =>
    request<Highlight>(`/api/documents/${id}/highlights`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteHighlight: (highlightId: string) =>
    request<void>(`/api/highlights/${highlightId}`, { method: "DELETE" }),
  getSummary: (id: string, length: SummaryLength) =>
    request<Summary>(`/api/documents/${id}/summary?length=${length}`),
  regenerateSummary: (id: string, length: SummaryLength) =>
    request<Summary>(`/api/documents/${id}/summary?length=${length}`, {
      method: "POST",
    }),
};
