import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

export interface Job {
  id: string;
  job_type: string;
  status: string;
  priority: "low" | "medium" | "high";
  backend: string | null;
  created_at: string;
  updated_at: string;
  duration_ms: number | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

export async function fetchJobs(): Promise<Job[]> {
  const { data } = await api.get<Job[]>("/jobs?limit=100");
  return data;
}

export async function fetchJob(id: string): Promise<Job> {
  const { data } = await api.get<Job>(`/jobs/${id}`);
  return data;
}

export async function submitVisionJob(
  file: File,
  task = "classify",
  priority: "low" | "medium" | "high" = "medium"
): Promise<Job> {
  const form = new FormData();
  form.append("job_type", "vision");
  form.append("file", file);
  form.append("task", task);
  form.append("priority", priority);
  const { data } = await api.post<Job>("/jobs", form);
  return data;
}

export async function submitLlmJob(
  prompt: string,
  task = "generate",
  maxTokens = 256,
  priority: "low" | "medium" | "high" = "medium"
): Promise<Job> {
  const form = new FormData();
  form.append("job_type", "llm");
  form.append("prompt", prompt);
  form.append("task", task);
  form.append("max_tokens", String(maxTokens));
  form.append("priority", priority);
  const { data } = await api.post<Job>("/jobs", form);
  return data;
}

export async function submitBatchVisionJobs(
  files: File[],
  task = "classify",
  priority: "low" | "medium" | "high" = "medium"
): Promise<Job[]> {
  const form = new FormData();
  form.append("task", task);
  form.append("priority", priority);
  for (const file of files) {
    form.append("files", file);
  }
  const { data } = await api.post<Job[]>("/jobs/batch", form);
  return data;
}

export async function cancelJob(id: string): Promise<void> {
  await api.delete(`/jobs/${id}`);
}

export async function fetchHealth(): Promise<{ status: string; checks: Record<string, string> }> {
  const { data } = await api.get("/ready");
  return data;
}
