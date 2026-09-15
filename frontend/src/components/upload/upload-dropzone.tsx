"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { FileTextIcon, UploadCloudIcon } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn, formatBytes } from "@/lib/utils";

interface Props {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}

export function UploadDropzone({ onUpload, disabled }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    setError(null);
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    noClick: true,
    // The classic <input type="file"> works everywhere (mobile browsers, plain
    // HTTP on the LAN); the File System Access API does not.
    useFsAccessApi: false,
    disabled: disabled || busy,
    onDropRejected: () => setError("只支援 PDF 檔案。"),
  });

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await onUpload(file);
    } catch (e) {
      setError(e instanceof Error ? e.message : "上傳失敗");
      setBusy(false);
    }
  };

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={cn(
          "flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed px-6 py-14 text-center transition-colors",
          isDragActive
            ? "border-foreground/60 bg-muted/60"
            : "border-border bg-card hover:border-foreground/30",
        )}
      >
        <input {...getInputProps({ id: "pdf-file-input" })} />
        <div className="flex size-12 items-center justify-center rounded-full bg-muted">
          <UploadCloudIcon className="size-6 text-muted-foreground" />
        </div>
        <div className="space-y-1">
          <p className="text-base font-medium">Drop your research paper here</p>
          <p className="text-sm text-muted-foreground">or</p>
        </div>
        {/* A label bound to the real file input opens the picker natively on every browser. */}
        <label
          htmlFor="pdf-file-input"
          className={cn(
            buttonVariants({ variant: "outline" }),
            "cursor-pointer",
            (disabled || busy) && "pointer-events-none opacity-50",
          )}
        >
          Choose PDF
        </label>
        <p className="text-xs text-muted-foreground">目前僅支援 .pdf</p>
      </div>

      {file && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border bg-card px-4 py-3">
          <FileTextIcon className="size-5 shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
          </div>
          <Button onClick={submit} disabled={busy}>
            {busy ? "上傳中…" : "開始解析"}
          </Button>
        </div>
      )}

      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
    </div>
  );
}
