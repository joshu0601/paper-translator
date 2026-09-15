"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BookOpenIcon, FileTextIcon, SparklesIcon, Trash2Icon } from "lucide-react";
import { api } from "@/lib/api";
import type { PaperDocument } from "@/types";
import { UploadDropzone } from "@/components/upload/upload-dropzone";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatBytes, formatDate } from "@/lib/utils";

const STATUS_LABEL: Record<PaperDocument["status"], string> = {
  uploaded: "已上傳",
  processing: "處理中",
  ready: "就緒",
  failed: "失敗",
};

export default function HomePage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<PaperDocument[] | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [demoBusy, setDemoBusy] = useState(false);

  const refresh = useCallback(() => {
    return api
      .listDocuments()
      .then((docs) => {
        setDocuments(docs);
        setBackendError(null);
      })
      .catch((e: unknown) => {
        setBackendError(e instanceof Error ? e.message : String(e));
        setDocuments([]);
      });
  }, []);

  useEffect(() => {
    // Async fetch; state is only set inside the promise callbacks.
    void refresh();
  }, [refresh]);

  const onUpload = async (file: File) => {
    const doc = await api.uploadDocument(file);
    router.push(`/papers/${doc.id}`);
  };

  const onDemo = async () => {
    setDemoBusy(true);
    try {
      const doc = await api.createDemoDocument();
      router.push(`/papers/${doc.id}`);
    } catch (e) {
      setBackendError(e instanceof Error ? e.message : String(e));
      setDemoBusy(false);
    }
  };

  const onDelete = async (id: string) => {
    await api.deleteDocument(id);
    refresh();
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-12 items-center justify-between border-b px-5">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <BookOpenIcon className="size-4" />
          PaperAI
        </div>
        <ThemeToggle />
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 py-12">
        <div className="mb-8 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            AI Academic Reading Workspace
          </h1>
          <p className="text-sm text-muted-foreground">
            上傳英文論文，系統會解析結構、產生繁體中文對照翻譯，並建立可引用來源的 AI 問答索引。
          </p>
        </div>

        <UploadDropzone onUpload={onUpload} />

        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            沒有 PDF？先用內建的範例論文體驗完整流程。
          </p>
          <Button variant="ghost" size="sm" onClick={onDemo} disabled={demoBusy}>
            <SparklesIcon />
            {demoBusy ? "建立中…" : "Try demo paper"}
          </Button>
        </div>

        {backendError && (
          <div className="mt-6 rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm">
            <p className="font-medium text-destructive">無法連線到後端</p>
            <p className="mt-1 text-muted-foreground">
              {backendError} — 請確認 FastAPI 已在{" "}
              <code className="font-mono text-xs">http://localhost:8000</code> 啟動。
            </p>
          </div>
        )}

        <section className="mt-12">
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">最近的論文</h2>
          {documents === null ? (
            <p className="text-sm text-muted-foreground">載入中…</p>
          ) : documents.length === 0 ? (
            <p className="text-sm text-muted-foreground">還沒有任何論文。</p>
          ) : (
            <ul className="divide-y rounded-lg border">
              {documents.map((doc) => (
                <li key={doc.id} className="flex items-center gap-3 px-4 py-3">
                  <FileTextIcon className="size-4 shrink-0 text-muted-foreground" />
                  <Link
                    href={`/papers/${doc.id}`}
                    className="min-w-0 flex-1 hover:underline"
                  >
                    <p className="truncate text-sm font-medium">{doc.title || doc.fileName}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {doc.fileName} · {formatBytes(doc.fileSize)} · {doc.pageCount} 頁 ·{" "}
                      {formatDate(doc.createdAt)}
                    </p>
                  </Link>
                  <Badge variant={doc.status === "failed" ? "destructive" : "secondary"}>
                    {STATUS_LABEL[doc.status]}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="刪除"
                    onClick={() => onDelete(doc.id)}
                  >
                    <Trash2Icon />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}
