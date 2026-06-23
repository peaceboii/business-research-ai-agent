"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2, CheckCircle2, Search, ArrowRight, ShieldCheck, HelpCircle, Terminal } from "lucide-react";

function ResearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get("id");

  const [status, setStatus] = useState("pending");
  const [message, setMessage] = useState("Initializing research run...");
  const [logs, setLogs] = useState<string[]>([]);
  const [businesses, setBusinesses] = useState<any[]>([]);
  const [stats, setStats] = useState({
    discovered: 0,
    deduplicated: 0,
    verified: 0,
  });

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!queryId) return;

    // Connect to SSE stream
    const eventSource = new EventSource(`http://127.0.0.1:8000/api/research/${queryId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { status: eventStatus, message: eventMessage, data } = payload;
        
        setStatus(eventStatus);
        setMessage(eventMessage);
        
        // Add message to terminal logs
        setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${eventMessage}`]);

        if (eventStatus === "discovering") {
          // Discovery stage
        } else if (eventStatus === "discovered") {
          // e.g. "Found 24 candidates."
          const match = eventMessage.match(/Found (\d+)/);
          if (match) {
            setStats((prev) => ({ ...prev, discovered: parseInt(match[1]) }));
          }
        } else if (eventStatus === "deduplicated") {
          // e.g. "Deduplication complete. Grouped into 12 unique entities."
          const match = eventMessage.match(/Grouped into (\d+)/);
          if (match) {
            setStats((prev) => ({ 
              ...prev, 
              deduplicated: prev.discovered - parseInt(match[1]),
              verified: parseInt(match[1])
            }));
          }
        } else if (eventStatus === "business_discovered" && data) {
          // Individual business verified and progressive streaming item
          setBusinesses((prev) => [data, ...prev]);
        } else if (eventStatus === "completed") {
          eventSource.close();
          // After 2.5 seconds, redirect to the report page
          setTimeout(() => {
            router.push(`/reports/${queryId}`);
          }, 2500);
        } else if (eventStatus === "failed") {
          eventSource.close();
        }
      } catch (e) {
        console.error("Error parsing SSE data:", e);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      setLogs((prev) => [...prev, `[ERROR] EventSource connection closed or failed.`]);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [queryId, router]);

  // Scroll terminal logs to bottom automatically
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Step indicator state
  const steps = [
    { name: "Query Parse", status: status === "parsing" ? "active" : ["discovering", "discovered", "deduplicated", "verifying", "business_discovered", "completed"].includes(status) ? "done" : "idle" },
    { name: "Multi-Source Search", status: status === "discovering" ? "active" : ["discovered", "deduplicated", "verifying", "business_discovered", "completed"].includes(status) ? "done" : "idle" },
    { name: "Fuzzy Deduplication", status: status === "discovered" || status === "deduplicated" ? "active" : ["verifying", "business_discovered", "completed"].includes(status) ? "done" : "idle" },
    { name: "Verification & Merge", status: status === "verifying" || status === "business_discovered" ? "active" : ["completed"].includes(status) ? "done" : "idle" },
  ];

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
            <span>Active Research Run #{queryId}</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">{message}</p>
        </div>
        <div className="flex space-x-4">
          <div className="card-3d px-4 py-2 rounded-lg text-center">
            <div className="text-xs text-slate-500 font-mono">Found</div>
            <div className="text-lg font-bold text-slate-300 font-mono">{stats.discovered}</div>
          </div>
          <div className="card-3d px-4 py-2 rounded-lg text-center">
            <div className="text-xs text-slate-500 font-mono">Duplicates Merged</div>
            <div className="text-lg font-bold text-violet-400 font-mono">{stats.deduplicated}</div>
          </div>
          <div className="card-3d px-4 py-2 rounded-lg text-center">
            <div className="text-xs text-slate-500 font-mono">Verified Entities</div>
            <div className="text-lg font-bold text-indigo-400 font-mono">{businesses.length}</div>
          </div>
        </div>
      </div>

      {/* Stepper Progress */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {steps.map((step, idx) => (
          <div
            key={idx}
            className={`card-3d p-4 rounded-xl space-y-2 transition-all duration-300 ${
              step.status === "done"
                ? "border-emerald-500/20 bg-emerald-500/5 text-slate-300"
                : step.status === "active"
                ? "border-indigo-500 bg-indigo-500/5 text-white"
                : "text-slate-500"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold">Step 0{idx + 1}</span>
              {step.status === "done" && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
              {step.status === "active" && <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />}
            </div>
            <div className="font-semibold text-sm">{step.name}</div>
          </div>
        ))}
      </div>

      {/* Main Grid: Logs + Live Results */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Terminal Logs (1 col) */}
        <div className="card-3d rounded-2xl overflow-hidden flex flex-col h-[500px]">
          <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex items-center space-x-2">
            <Terminal className="h-4 w-4 text-indigo-400" />
            <span className="font-mono text-xs font-semibold text-slate-300">Crawler Terminal Logs</span>
          </div>
          <div className="p-4 flex-1 overflow-y-auto font-mono text-xs text-slate-400 space-y-2 h-full">
            {logs.map((log, idx) => (
              <div key={idx} className="whitespace-pre-wrap leading-relaxed border-l-2 border-slate-800 pl-2">
                {log}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>

        {/* Live Discovered Businesses (2 cols) */}
        <div className="md:col-span-2 card-3d p-6 rounded-2xl flex flex-col h-[500px]">
          <h2 className="text-base font-bold text-white mb-4 flex items-center justify-between">
            <span>Streaming Verified Profiles</span>
            <span className="text-xs font-mono text-slate-500">Real-Time stream ({businesses.length} loaded)</span>
          </h2>
          
          <div className="flex-1 overflow-y-auto space-y-3 pr-2">
            {businesses.length > 0 ? (
              businesses.map((biz) => (
                <div
                  key={biz.id || biz.business_name}
                  className="card-3d p-4 rounded-xl flex items-start justify-between gap-4"
                >
                  <div className="space-y-1">
                    <h3 className="font-semibold text-white text-sm">{biz.business_name}</h3>
                    <p className="text-slate-400 text-xs">{biz.address || "No address found"}</p>
                    <div className="flex flex-wrap gap-2 pt-1.5">
                      {biz.phone && (
                        <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                          📞 {biz.phone}
                        </span>
                      )}
                      {biz.website && (
                        <span className="text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded font-mono">
                          🌐 {biz.website.replace("https://", "").replace("http://", "").split("/")[0]}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right flex flex-col items-end justify-between self-stretch">
                    <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 px-2 py-1 rounded text-xs">
                      <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
                      <span className="font-bold text-white font-mono">{biz.verification_score}</span>
                    </div>
                    {biz.rating && (
                      <span className="text-[11px] text-amber-400 font-semibold font-mono">
                        ⭐ {biz.rating} ({biz.review_count})
                      </span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-2">
                <Loader2 className="h-6 w-6 animate-spin text-slate-700" />
                <span className="text-xs">Gathering candidate matches...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ResearchPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    }>
      <ResearchContent />
    </Suspense>
  );
}
