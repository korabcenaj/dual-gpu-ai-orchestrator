import clsx from "clsx";
import { Job, cancelJob } from "../api/client";
import { useQueryClient } from "react-query";

const STATUS_COLORS: Record<string, string> = {
  pending:   "bg-gray-700 text-gray-300",
  queued:    "bg-blue-900 text-blue-300",
  running:   "bg-yellow-900 text-yellow-300 animate-pulse",
  completed: "bg-green-900 text-green-300",
  failed:    "bg-red-900 text-red-300",
  cancelled: "bg-gray-700 text-gray-500",
};

const BACKEND_COLORS: Record<string, string> = {
  "intel-igpu-openvino": "text-sky-400",
  "amd-wx3100-vulkan":   "text-orange-400",
};

export default function JobTable({
  jobs,
  isLoading,
}: {
  jobs: Job[];
  isLoading: boolean;
}) {
  const qc = useQueryClient();

  const handleCancel = async (id: string) => {
    await cancelJob(id);
    qc.invalidateQueries("jobs");
  };

  if (isLoading) {
    return <div className="text-gray-500 text-sm">Loading jobs…</div>;
  }
  if (jobs.length === 0) {
    return (
      <div className="text-center text-gray-600 py-20">
        No jobs yet. Go to Submit to create one.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead className="bg-gray-900 text-gray-400 text-xs uppercase tracking-wider">
          <tr>
            {["ID", "Type", "Backend", "Status", "Duration", "Created", ""].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {jobs.map((job) => (
            <tr key={job.id} className="hover:bg-gray-900 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-gray-400">
                {job.id.slice(0, 8)}…
              </td>
              <td className="px-4 py-3 font-medium capitalize">{job.job_type}</td>
              <td className={clsx("px-4 py-3 font-mono text-xs",
                BACKEND_COLORS[job.backend ?? ""] ?? "text-gray-500")}>
                {job.backend ?? "—"}
              </td>
              <td className="px-4 py-3">
                <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium",
                  STATUS_COLORS[job.status] ?? "bg-gray-700 text-gray-300")}>
                  {job.status}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-400 tabular-nums">
                {job.duration_ms != null ? `${job.duration_ms} ms` : "—"}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {new Date(job.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-3">
                {(job.status === "queued" || job.status === "pending") && (
                  <button
                    onClick={() => handleCancel(job.id)}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    Cancel
                  </button>
                )}
                {job.status === "completed" && job.result && (
                  <details className="cursor-pointer">
                    <summary className="text-xs text-violet-400 hover:text-violet-300">
                      View
                    </summary>
                    <pre className="mt-1 text-xs bg-gray-800 rounded p-2 max-w-sm overflow-auto">
                      {JSON.stringify(job.result, null, 2)}
                    </pre>
                  </details>
                )}
                {job.status === "failed" && (
                  <span className="text-xs text-red-400" title={job.error ?? ""}>
                    ⚠ Error
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
