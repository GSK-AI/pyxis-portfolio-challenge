"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  playthroughDataSchema,
  type PlaythroughData,
} from "@/lib/definitionsGameZ";
import LayoutContainer from "@/components/LayoutContainer";

interface FileUploadAreaProps {
  onPlaythroughLoaded: (data: PlaythroughData) => void;
  onCancel: () => void;
}

export default function FileUploadArea({
  onPlaythroughLoaded,
  onCancel,
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

  return (
    <div className="mt-4">
      <LayoutContainer className="flex flex-col gap-6" maxWidth="600px">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Upload Replay</h2>
          <Button variant="outline" size="sm" onClick={onCancel}>
            <X className="mr-1 h-4 w-4" />
            Cancel
          </Button>
        </div>

        {!preview ? (
          <>
            <div
              className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors ${
                dragging
                  ? "border-teal-500 bg-teal-50"
                  : "border-gray-300 bg-gray-50 hover:border-gray-400"
              }`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              <Upload className="mb-3 h-10 w-10 text-gray-400" />
              <p className="text-sm font-medium text-gray-700">
                Drop a playthrough JSON file here
              </p>
              <p className="mt-1 text-xs text-gray-500">or click to browse</p>
              <input
                ref={inputRef}
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleFileInput}
              />
            </div>

            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                {error}
              </div>
            )}
          </>
        ) : (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="mb-4 flex items-center gap-3">
              <FileText className="h-8 w-8 text-teal-600" />
              <div>
                <p className="text-sm font-semibold">{preview.fileName}</p>
                <p className="text-xs text-gray-500">
                  Captured{" "}
                  {new Date(preview.data.metadata.captured_at).toLocaleString()}
                </p>
              </div>
            </div>

            <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded bg-gray-50 p-3">
                <span className="text-xs text-gray-500">Agents</span>
                <p className="font-medium">
                  {preview.data.metadata.num_agents}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">
                  {preview.data.metadata.agent_ids
                    .map((id) => preview.data.metadata.agent_names?.[id] ?? id)
                    .join(", ")}
                </p>
              </div>
              <div className="rounded bg-gray-50 p-3">
                <span className="text-xs text-gray-500">Horizon</span>
                <p className="font-medium">
                  {preview.data.metadata.horizon} steps
                </p>
              </div>
              <div className="rounded bg-gray-50 p-3">
                <span className="text-xs text-gray-500">Total Steps</span>
                <p className="font-medium">{preview.data.steps.length}</p>
              </div>
              <div className="rounded bg-gray-50 p-3">
                <span className="text-xs text-gray-500">Seed</span>
                <p className="font-medium">{preview.data.metadata.seed}</p>
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                onClick={() => onPlaythroughLoaded(preview.data)}
                className="flex-1"
              >
                Load Replay
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setPreview(null);
                  setError(null);
                }}
              >
                Choose Different File
              </Button>
            </div>
          </div>
        )}
      </LayoutContainer>
    </div>
  );
}
