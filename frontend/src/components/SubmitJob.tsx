import { useState, useRef } from "react";
import { submitVisionJob, submitLlmJob } from "../api/client";

export default function SubmitJob({ onSubmitted }: { onSubmitted: () => void }) {
  const [jobType, setJobType] = useState<"vision" | "llm">("llm");
  const [prompt, setPrompt] = useState("");
  const [task, setTask] = useState("generate");
  const [maxTokens, setMaxTokens] = useState(256);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (jobType === "vision") {
        if (!file) { setError("Select an image file"); return; }
        await submitVisionJob(file, task);
      } else {
        if (!prompt.trim()) { setError("Enter a prompt"); return; }
        await submitLlmJob(prompt.trim(), task, maxTokens);
      }
      onSubmitted();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl">
      <h2 className="text-lg font-semibold mb-4">Submit Inference Job</h2>
      <form onSubmit={handleSubmit} className="space-y-5">

        {/* Job type selector */}
        <div className="flex gap-3">
          {(["llm", "vision"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => { setJobType(t); setTask(t === "llm" ? "generate" : "classify"); }}
              className={`flex-1 py-2 rounded-lg border text-sm font-medium transition-colors ${
                jobType === t
                  ? "border-violet-500 bg-violet-950 text-violet-300"
                  : "border-gray-700 text-gray-400 hover:border-gray-500"
              }`}
            >
              {t === "llm" ? "🧠 LLM (AMD Vulkan)" : "👁 Vision (Intel OpenVINO)"}
            </button>
          ))}
        </div>

        {/* Task */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Task</label>
          <select
            value={task}
            onChange={(e) => setTask(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
          >
            {jobType === "llm"
              ? ["generate", "summarize", "classify"].map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))
              : ["classify", "detect"].map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
          </select>
        </div>

        {/* LLM prompt */}
        {jobType === "llm" && (
          <>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={5}
                maxLength={4096}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm resize-y"
                placeholder="Enter your text or question…"
              />
              <div className="text-xs text-gray-600 text-right">{prompt.length}/4096</div>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Max tokens: <strong>{maxTokens}</strong>
              </label>
              <input
                type="range" min={64} max={512} step={64}
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="w-full accent-violet-500"
              />
            </div>
          </>
        )}

        {/* Vision file */}
        {jobType === "vision" && (
          <div>
            <label className="block text-sm text-gray-400 mb-1">Image file</label>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block text-sm text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-violet-900 file:text-violet-200 file:cursor-pointer"
            />
            {file && <div className="text-xs text-gray-500 mt-1">{file.name}</div>}
          </div>
        )}

        {error && (
          <div className="text-sm text-red-400 bg-red-950 border border-red-800 rounded px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
        >
          {submitting ? "Submitting…" : "Submit Job"}
        </button>
      </form>
    </div>
  );
}
