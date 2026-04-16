import { useState, type ReactNode } from "react";
import { useQuery } from "react-query";
import { Activity, Cpu, Layers, PlusCircle } from "lucide-react";
import JobTable from "./components/JobTable";
import SubmitJob from "./components/SubmitJob";
import MetricsPanel from "./components/MetricsPanel";
import HealthBadge from "./components/HealthBadge";
import { fetchJobs } from "./api/client";
import { useJobWebSocket, JobStatusMessage } from "./hooks/useJobWebSocket";
import JobStatusToaster from "./components/JobStatusToaster";

type Tab = "jobs" | "submit" | "metrics";

export default function App() {
  const [tab, setTab] = useState<Tab>("jobs");
  const { data: jobs = [], isLoading, refetch } = useQuery("jobs", fetchJobs);
  const [toastMsg, setToastMsg] = useState<JobStatusMessage | null>(null);
  const jobsRef = useRef(jobs);
  jobsRef.current = jobs;

  // WebSocket: update job table and show toast
  const handleJobStatus = useCallback((msg: JobStatusMessage) => {
    setToastMsg(msg);
    // Optionally, refetch jobs or optimistically update job table here
    refetch();
  }, [refetch]);
  useJobWebSocket(handleJobStatus);

  const pending = jobs.filter((j) => j.status === "running" || j.status === "queued").length;
  const completed = jobs.filter((j) => j.status === "completed").length;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cpu className="text-violet-400 w-6 h-6" />
          <h1 className="text-lg font-semibold tracking-tight">Dual-GPU AI Orchestrator</h1>
          <span className="text-xs text-gray-500 font-mono">Intel HD 530 + AMD WX 3100</span>
        </div>
        <HealthBadge />
      </header>

      {/* Stats bar */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-2 flex gap-8 text-sm text-gray-400">
        <span>Total jobs: <strong className="text-white">{jobs.length}</strong></span>
        <span>Active: <strong className="text-yellow-400">{pending}</strong></span>
        <span>Completed: <strong className="text-green-400">{completed}</strong></span>
      </div>

      {/* Tab nav */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6 flex gap-1">
        {(
          [
            { id: "jobs", label: "Jobs", icon: <Layers className="w-4 h-4" /> },
            { id: "submit", label: "Submit", icon: <PlusCircle className="w-4 h-4" /> },
            { id: "metrics", label: "Metrics", icon: <Activity className="w-4 h-4" /> },
          ] as { id: Tab; label: string; icon: ReactNode }[]
        ).map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm border-b-2 transition-colors ${
              tab === id
                ? "border-violet-500 text-violet-300"
                : "border-transparent text-gray-400 hover:text-white"
            }`}
          >
            {icon} {label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="flex-1 p-6">
        {tab === "jobs" && <JobTable jobs={jobs} isLoading={isLoading} />}
        {tab === "submit" && <SubmitJob onSubmitted={() => setTab("jobs")} />}
        {tab === "metrics" && <MetricsPanel jobs={jobs} />}
      </main>
      <JobStatusToaster message={toastMsg} />
    </div>
  );
}
