"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Play, Calendar, CheckCircle2, AlertCircle, ArrowRight, Loader2, Sparkles, Clock, Trash } from "lucide-react";

interface StatItem {
  total_queries: number;
  total_businesses: number;
  total_reports: number;
  duplicates_removed_total: number;
  avg_duration: number;
  recent_activity: Array<{
    query_id: number;
    query_text: string;
    status: string;
    created_at: string;
  }>;
}

const getApiBase = () => {
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000/api`;
  }
  return "http://127.0.0.1:8000/api";
};

export default function Dashboard() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<StatItem | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const sampleQueries = [
    "Cardiologists in Birmingham",
    "Dentists in Austin",
    "Roofing contractors in Dallas",
    "Family lawyers in Chicago",
    "Plumbers in Houston",
  ];

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${getApiBase()}/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Error fetching stats:", e);
    } finally {
      setStatsLoading(false);
    }
  };

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${getApiBase()}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery }),
      });
      if (res.ok) {
        const data = await res.json();
        router.push(`/research?id=${data.id}`);
      } else {
        alert("Failed to trigger research. Please check backend connection.");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to connect to backend server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto space-y-4 py-6">
        <div className="inline-flex items-center space-x-2 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-3 py-1 rounded-full text-sm font-semibold">
          <Sparkles className="h-4 w-4" />
          <span>Autonomous Research Pipeline</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
          AI-Powered Business Research Agent
        </h1>
        <p className="text-slate-400 text-lg">
          Discovers businesses, crawls official websites, cross-checks listings, detects conflicts, and resolves duplicates automatically.
        </p>
      </div>

      {/* Search Container */}
      <div className="max-w-2xl mx-auto card-3d p-6 rounded-2xl backdrop-blur-md">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(query);
          }}
          className="flex space-x-2"
        >
          <div className="relative flex-1">
            <Search className="absolute left-4 top-3.5 h-5 w-5 text-slate-500" />
            <input
              type="text"
              placeholder="What category and location are you researching?..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-xl py-3.5 pl-12 pr-4 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-sm placeholder:text-slate-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-3d text-white font-semibold px-6 rounded-xl flex items-center space-x-2 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                <span>Search</span>
              </>
            )}
          </button>
        </form>

        {/* Suggestions */}
        <div className="mt-4 flex flex-wrap gap-2 items-center">
          <span className="text-xs text-slate-500 font-medium mr-1">Examples:</span>
          {sampleQueries.map((sq, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setQuery(sq);
                handleSearch(sq);
              }}
              disabled={loading}
              className="text-xs bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Section */}
      <div className="space-y-6">
        <h2 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2">
          <span>Operational Dashboard</span>
        </h2>
        {statsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-28 bg-slate-900/40 border border-slate-800 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="card-3d p-5 rounded-xl space-y-2">
              <div className="text-sm text-slate-400 font-medium">Total Queries Run</div>
              <div className="text-3xl font-bold text-white font-mono">{stats?.total_queries || 0}</div>
            </div>
            <div className="card-3d p-5 rounded-xl space-y-2">
              <div className="text-sm text-slate-400 font-medium">Verified Businesses</div>
              <div className="text-3xl font-bold text-indigo-400 font-mono">{stats?.total_businesses || 0}</div>
            </div>
            <div className="card-3d p-5 rounded-xl space-y-2">
              <div className="text-sm text-slate-400 font-medium">Duplicates Merged</div>
              <div className="text-3xl font-bold text-violet-400 font-mono">{stats?.duplicates_removed_total || 0}</div>
            </div>
            <div className="card-3d p-5 rounded-xl space-y-2">
              <div className="text-sm text-slate-400 font-medium">Avg Crawl Duration</div>
              <div className="text-3xl font-bold text-emerald-400 font-mono flex items-baseline space-x-1">
                <span>{stats?.avg_duration || 0}</span>
                <span className="text-sm font-medium text-slate-500">sec</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recent Activity Table */}
      <div className="space-y-6">
        <h2 className="text-xl font-bold tracking-tight text-white">Recent Research Runs</h2>
        <div className="card-3d rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40 text-xs text-slate-400 uppercase font-semibold font-mono">
                  <th className="px-6 py-4">Query Run</th>
                  <th className="px-6 py-4">Triggered Time</th>
                  <th className="px-6 py-4">Pipeline Status</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-sm">
                {stats?.recent_activity && stats.recent_activity.length > 0 ? (
                  stats.recent_activity.map((item) => (
                    <tr key={item.query_id} className="hover:bg-slate-900/20 transition-colors">
                      <td className="px-6 py-4 font-semibold text-white">{item.query_text}</td>
                      <td className="px-6 py-4 text-slate-400 flex items-center space-x-1">
                        <Clock className="h-3.5 w-3.5 text-slate-500" />
                        <span>{new Date(item.created_at).toLocaleString()}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
                            item.status === "completed"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : item.status === "running"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          }`}
                        >
                          {item.status === "completed" ? (
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          ) : (
                            <AlertCircle className="h-3.5 w-3.5" />
                          )}
                          <span className="capitalize">{item.status}</span>
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => {
                            if (item.status === "completed") {
                              router.push(`/reports/${item.query_id}`);
                            } else {
                              router.push(`/research?id=${item.query_id}`);
                            }
                          }}
                          className="inline-flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 font-semibold transition-colors cursor-pointer group text-xs"
                        >
                          <span>{item.status === "completed" ? "View Report" : "Track Progress"}</span>
                          <ArrowRight className="h-3.5 w-3.5 transform group-hover:translate-x-1 transition-transform" />
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-6 py-10 text-center text-slate-500">
                      No search runs triggered yet. Submit a query above to start!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
