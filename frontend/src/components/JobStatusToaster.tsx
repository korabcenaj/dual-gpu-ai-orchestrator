import { useEffect, useState } from "react";
import type { JobStatusMessage } from "../hooks/useJobWebSocket";

export default function JobStatusToaster({
  message,
}: {
  message: JobStatusMessage | null;
}) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (message) {
      setVisible(true);
      const t = setTimeout(() => setVisible(false), 3500);
      return () => clearTimeout(t);
    }
  }, [message]);
  if (!message || !visible) return null;
  return (
    <div className="fixed bottom-6 right-6 z-50 bg-gray-900 border border-violet-700 text-white px-6 py-3 rounded-lg shadow-lg flex flex-col gap-1 animate-fade-in">
      <span className="font-bold text-violet-300">Job {message.job_id.slice(0,8)}…</span>
      <span>Status: <span className="capitalize">{message.status}</span></span>
      {message.error && <span className="text-red-400">Error: {message.error}</span>}
      {message.backend && <span className="text-xs text-gray-400">Backend: {message.backend}</span>}
    </div>
  );
}
