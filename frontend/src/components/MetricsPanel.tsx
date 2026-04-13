import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from "recharts";
import { Job } from "../api/client";

function avg(nums: number[]) {
  return nums.length ? Math.round(nums.reduce((a, b) => a + b, 0) / nums.length) : 0;
}

export default function MetricsPanel({ jobs }: { jobs: Job[] }) {
  const completed = jobs.filter((j) => j.status === "completed" && j.duration_ms != null);

  // Latency by backend
  const byBackend: Record<string, number[]> = {};
  for (const j of completed) {
    const b = j.backend ?? "unknown";
    (byBackend[b] ??= []).push(j.duration_ms!);
  }
  const latencyData = Object.entries(byBackend).map(([backend, ms]) => ({
    backend: backend.replace("intel-igpu-openvino", "Intel").replace("amd-wx3100-vulkan", "AMD"),
    avg_ms: avg(ms),
    count: ms.length,
  }));

  // Throughput over time (jobs per minute)
  const now = Date.now();
  const buckets: Record<number, number> = {};
  for (const j of completed) {
    const minuteAgo = Math.floor((now - new Date(j.updated_at).getTime()) / 60000);
    if (minuteAgo <= 30) {
      (buckets[minuteAgo] ??= 0);
      buckets[minuteAgo]++;
    }
  }
  const throughputData = Array.from({ length: 31 }, (_, i) => ({
    min: `-${30 - i}m`,
    jobs: buckets[30 - i] ?? 0,
  }));

  // Status breakdown
  const statusCounts: Record<string, number> = {};
  for (const j of jobs) (statusCounts[j.status] ??= 0, statusCounts[j.status]++);
  const statusData = Object.entries(statusCounts).map(([status, count]) => ({ status, count }));

  return (
    <div className="space-y-8">
      <h2 className="text-lg font-semibold">Performance Metrics</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Total Jobs", value: jobs.length },
          { label: "Avg Latency (Intel)", value: avg(byBackend["intel-igpu-openvino"] ?? []) + " ms" },
          { label: "Avg Latency (AMD)", value: avg(byBackend["amd-wx3100-vulkan"] ?? []) + " ms" },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="text-gray-500 text-xs mb-1">{label}</div>
            <div className="text-2xl font-bold text-violet-300">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Avg Latency by Backend (ms)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={latencyData}>
              <XAxis dataKey="backend" tick={{ fill: "#9ca3af", fontSize: 12 }} />
              <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
              <Bar dataKey="avg_ms" fill="#7c3aed" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Status Breakdown</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={statusData}>
              <XAxis dataKey="status" tick={{ fill: "#9ca3af", fontSize: 12 }} />
              <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
              <Bar dataKey="count" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Completions Over Last 30 min</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={throughputData}>
            <XAxis dataKey="min" tick={{ fill: "#9ca3af", fontSize: 10 }} interval={4} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
            <Legend />
            <Line type="monotone" dataKey="jobs" stroke="#7c3aed" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
