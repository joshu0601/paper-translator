"use client";

import { use } from "react";
import { Workspace } from "@/components/workspace/workspace";

export default function PaperPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <Workspace documentId={id} />;
}
