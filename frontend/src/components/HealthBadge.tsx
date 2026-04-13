import { useQuery } from "react-query";
import { fetchHealth } from "../api/client";
import clsx from "clsx";

export default function HealthBadge() {
  const { data } = useQuery("health", fetchHealth, {
    refetchInterval: 10000,
    retry: false,
  });

  const ok = data?.status === "ok";
  return (
    <div className={clsx("flex items-center gap-1.5 text-xs font-mono",
      ok ? "text-green-400" : "text-yellow-400")}>
      <span className={clsx("w-2 h-2 rounded-full",
        ok ? "bg-green-400" : "bg-yellow-400 animate-pulse")} />
      {ok ? "All systems operational" : data?.status ?? "Checking…"}
    </div>
  );
}
