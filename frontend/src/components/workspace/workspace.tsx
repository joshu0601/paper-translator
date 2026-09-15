"use client";

import Link from "next/link";
import { usePaper } from "@/hooks/use-paper";
import { WorkspaceProvider, useWorkspace } from "./workspace-context";
import { WorkspaceHeader } from "./header";
import { PaperSidebar } from "@/components/paper-sidebar/sidebar";
import { PaperReader } from "@/components/paper-reader/reader";
import { AIPanel } from "@/components/ai-chat/ai-panel";
import { SearchDialog } from "@/components/search/search-dialog";
import { ProcessingProgress } from "@/components/upload/processing-progress";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export function Workspace({ documentId }: { documentId: string }) {
  const paper = usePaper(documentId);

  if (paper.error && !paper.document) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-sm text-destructive">{paper.error}</p>
        <Button variant="outline" render={<Link href="/" />}>
          回到首頁
        </Button>
      </div>
    );
  }

  if (!paper.document) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        載入中…
      </div>
    );
  }

  return (
    <WorkspaceProvider paper={paper}>
      <WorkspaceLayout />
    </WorkspaceProvider>
  );
}

function WorkspaceLayout() {
  const { paper, sidebarOpen, aiPanelOpen } = useWorkspace();
  const doc = paper.document!;
  const parsed = doc.steps.find((s) => s.key === "parse")?.status === "done";
  const showReader = parsed && paper.paragraphs.length > 0;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <WorkspaceHeader />
      <SearchDialog />

      {/* Desktop / tablet: three columns */}
      <div className="hidden min-h-0 flex-1 md:flex">
        <aside
          className={cn(
            "shrink-0 border-r bg-sidebar transition-[width] duration-200",
            sidebarOpen ? "w-64" : "w-0 overflow-hidden border-r-0",
          )}
        >
          <PaperSidebar />
        </aside>
        <main className="relative min-w-0 flex-1">
          {showReader ? (
            <PaperReader />
          ) : (
            <ProcessingView />
          )}
        </main>
        <aside
          className={cn(
            "shrink-0 border-l bg-background transition-[width] duration-200",
            aiPanelOpen ? "w-[380px] xl:w-[420px]" : "w-0 overflow-hidden border-l-0",
          )}
        >
          <AIPanel />
        </aside>
      </div>

      {/* Mobile: tabs (SPEC §50) */}
      <div className="flex min-h-0 flex-1 flex-col md:hidden">
        <Tabs defaultValue="paper" className="flex min-h-0 flex-1 flex-col">
          <TabsList className="mx-3 mt-2 grid grid-cols-3">
            <TabsTrigger value="paper">Paper</TabsTrigger>
            <TabsTrigger value="outline">Outline</TabsTrigger>
            <TabsTrigger value="ai">AI</TabsTrigger>
          </TabsList>
          <TabsContent value="paper" className="min-h-0 flex-1">
            {showReader ? <PaperReader /> : <ProcessingView />}
          </TabsContent>
          <TabsContent value="outline" className="min-h-0 flex-1">
            <PaperSidebar />
          </TabsContent>
          <TabsContent value="ai" className="min-h-0 flex-1">
            <AIPanel />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function ProcessingView() {
  const { paper } = useWorkspace();
  const doc = paper.document!;
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="w-full max-w-sm rounded-xl border bg-card p-6">
        <p className="mb-1 truncate text-sm font-medium">{doc.title || doc.fileName}</p>
        <p className="mb-5 text-xs text-muted-foreground">
          {doc.pageCount} 頁 · {doc.fileName}
        </p>
        <ProcessingProgress document={doc} />
        {doc.status === "failed" && (
          <div className="mt-5 flex gap-2">
            <Button className="flex-1" onClick={() => paper.reprocess()}>
              重新處理
            </Button>
            <Button className="flex-1" variant="outline" render={<Link href="/" />}>
              回到首頁
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
