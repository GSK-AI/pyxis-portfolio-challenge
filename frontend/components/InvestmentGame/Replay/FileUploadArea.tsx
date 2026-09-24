"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileText, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  playthroughDataSchema,
  type PlaythroughData,
} from "@/lib/definitionsGameZ";

interface FileUploadAreaProps {
  onPlaythroughLoaded: (data: PlaythroughData) => void;
}

export default function FileUploadArea({
  onPlaythroughLoaded,
}: FileUploadAreaProps) {
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    data: PlaythroughData;
    fileName: string;
  } | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback((file: File) => {
    setError(null);
    setPreview(null);

    if (!file.name.endsWith(".json")) {
      setError("Please upload a .json file");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const raw = JSON.parse(e.target?.result as string);
        const result = playthroughDataSchema.safeParse(raw);
        if (!result.success) {
          const issues = result.error.issues
            .slice(0, 3)
            .map((i) => `${i.path.join(".")}: ${i.message}`)
            .join("; ");
          setError(`Invalid playthrough file: ${issues}`);
          return;
        }
        setPreview({ data: result.data, fileName: file.name });
      } catch {
        setError("Failed to parse JSON file");
      }
    };
    reader.onerror = () => setError("Failed to read file");
    reader.readAsText(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  if (preview) {
    return (
      <div className="rounded bg-gradient-to-b from-secondary/50 to-secondary/10 p-5">
        <div className="mb-4 flex items-center gap-3">
          <FileText className="h-8 w-8 text-primary" />
          <div>
            <p className="text-sm font-bold">{preview.fileName}</p>
            <p className="text-xs text-muted-foreground">
              Captured{" "}
              {new Date(preview.data.metadata.captured_at).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded bg-card p-3 ring-1 ring-foreground/5">
            <span className="text-xs text-muted-foreground">Agents</span>
            <p className="font-bold">{preview.data.metadata.num_agents}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {preview.data.metadata.agent_ids
                .map((id) => preview.data.metadata.agent_names?.[id] ?? id)
                .join(", ")}
            </p>
          </div>
          <div className="rounded bg-card p-3 ring-1 ring-foreground/5">
            <span className="text-xs text-muted-foreground">Horizon</span>
            <p className="font-bold">{preview.data.metadata.horizon} steps</p>
          </div>
          <div className="rounded bg-card p-3 ring-1 ring-foreground/5">
            <span className="text-xs text-muted-foreground">Total Steps</span>
            <p className="font-bold">{preview.data.steps.length}</p>
          </div>
          <div className="rounded bg-card p-3 ring-1 ring-foreground/5">
            <span className="text-xs text-muted-foreground">Seed</span>
            <p className="font-bold">{preview.data.metadata.seed}</p>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            size="lg"
            className="flex-1 rounded"
            onClick={() => onPlaythroughLoaded(preview.data)}
          >
            Load Replay
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="rounded"
            onClick={() => {
              setPreview(null);
              setError(null);
            }}
          >
            Choose Different File
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div
        className={`flex cursor-pointer flex-col items-center justify-center rounded border border-dashed p-12 transition-colors ${
          dragging
            ? "border-primary bg-[var(--accent-soft)]"
            : "border-input bg-gradient-to-b from-secondary/50 to-secondary/10 hover:border-primary/50"
        }`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-[var(--accent-soft)]">
          <Upload className="size-5 text-primary" />
        </div>
        <p className="text-sm font-bold">Drop a playthrough JSON file here</p>
        <p className="mt-1 text-sm text-muted-foreground">or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept=".json"
          className="hidden"
          onChange={handleFileInput}
        />
      </div>

      {error && (
        <div className="rounded bg-destructive/5 px-3 py-1.5 text-sm text-destructive">
          <div className="flex items-start gap-2">
            <TriangleAlert className="mt-[3px] size-4 shrink-0" />
            <span>{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
