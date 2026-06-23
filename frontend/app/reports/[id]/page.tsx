"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  PieChart, Pie, Cell, RadialBarChart, RadialBar 
} from "recharts";
import { 
  ShieldCheck, Trash2, Clock, Globe, ArrowLeft, Loader2, FileText, CheckCircle2 
} from "lucide-react";

interface Report {
  id: number;
  query_id: number;
  duration: number;
  total_discovered: number;
  total_verified: number;
  duplicates_removed: number;
  sources_used: number;
  website_coverage: number;
  phone_coverage: number;
  hours_coverage: number;
  report_markdown: string;
}

export default function ReportPage({ params: paramsPromise }: { params: Promise<{ id: string }> }) {
  const params = use(paramsPromise);
  const router = useRouter();
  const queryId = params.id;

  const [report, setReport] = useState<any | null>(null);
  const [businesses, setBusinesses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (queryId) {
      fetchReportAndBusinesses();
    }
  }, [queryId]);

  const fetchReportAndBusinesses = async () => {
    setLoading(true);
    try {
      // Fetch report
      const repRes = await fetch(`http://127.0.0.1:8000/api/reports/${queryId}`);
      let repData = null;
      if (repRes.ok) {
        repData = await repRes.json();
        setReport(repData);
      }

      // Fetch all businesses for this query to build charts
      const bizRes = await fetch(`http://127.0.0.1:8000/api/businesses?query_id=${queryId}&limit=500`);
      if (bizRes.ok) {
        const bizData = await bizRes.json();
        setBusinesses(bizData);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        <span className="text-slate-400 text-sm">Generating visual reports...</span>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="text-center py-20 space-y-4">
        <div className="text-slate-500 text-sm">No report found for query run #{queryId}</div>
        <button
          onClick={() => router.push("/")}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-xl transition-all cursor-pointer text-sm"
        >
          Go back home
        </button>
      </div>
    );
  }

  // 1. Process Chart Data: Coverage Data
  const coverageData = [
    { name: "Website", percentage: report.website_coverage, fill: "#6366f1" },
    { name: "Phone", percentage: report.phone_coverage, fill: "#10b981" },
    { name: "Hours", percentage: report.hours_coverage, fill: "#8b5cf6" },
  ];

  // 2. Process Chart Data: Verification score distribution
  let highVerified = 0; // 80-100
  let modVerified = 0;  // 60-80
  let lowVerified = 0;  // 0-60
  
  businesses.forEach((b) => {
    const score = b.verification_score || 0.0;
    if (score >= 80) highVerified++;
    else if (score >= 60) modVerified++;
    else lowVerified++;
  });

  const distributionData = [
    { name: "Highly Verified (80-100)", value: highVerified, color: "#10b981" },
    { name: "Verified (60-80)", value: modVerified, color: "#6366f1" },
    { name: "Unverified (<60)", value: lowVerified, color: "#ef4444" },
  ].filter(item => item.value > 0);

  // 3. Process Chart Data: Source Contributions
  const sourceCounts: { [key: string]: number } = {};
  businesses.forEach((b) => {
    const sourceUrls = b.source_urls || {};
    const seenSources = new Set<string>();
    
    // Aggregate all source keys
    Object.values(sourceUrls).forEach((urls: any) => {
      if (Array.isArray(urls)) {
        urls.forEach((url) => {
          let srcName = "website";
          const platforms = ["yelp", "yellowpages", "linkedin", "facebook", "healthgrades", "avvo", "angi", "duckduckgo"];
          for (const p of platforms) {
            if (url.toLowerCase().includes(p)) {
              srcName = p;
              break;
            }
          }
          seenSources.add(srcName);
        });
      }
    });

    seenSources.forEach((src) => {
      sourceCounts[src] = (sourceCounts[src] || 0) + 1;
    });
  });

  const sourceData = Object.entries(sourceCounts).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value
  })).sort((a, b) => b.value - a.value);

  // Parse markdown basic bolding/bullet formatting to display nicely in Tailwind UI
  const formatReportMarkdown = (md: string) => {
    if (!md) return "";
    return md
      .replace(/^# (.*)$/gm, '<h1 class="text-2xl font-bold text-white mt-6 mb-4">$1</h1>')
      .replace(/^## (.*)$/gm, '<h2 class="text-xl font-semibold text-white mt-5 mb-3 border-b border-slate-800 pb-2">$1</h2>')
      .replace(/^### (.*)$/gm, '<h3 class="text-lg font-medium text-slate-200 mt-4 mb-2">$1</h3>')
      .replace(/^\* (.*)$/gm, '<li class="ml-4 list-disc text-slate-300 py-1">$1</li>')
      .replace(/^\| (.*) \|$/gm, '<tr class="border-b border-slate-800">$1</tr>')
      .replace(/__(.*?)__/g, '<strong>$1</strong>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '<br/>');
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-6">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => router.push("/")}
            className="p-2 border border-slate-800 rounded-xl hover:bg-slate-900 text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-3xl font-extrabold text-white">Research Analytical Report</h1>
            <p className="text-slate-400 text-sm mt-1">Audit verification metrics and duplicates detection details.</p>
          </div>
        </div>

        <button
          onClick={() => router.push(`/businesses?query_id=${report.query_id}`)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-600/20 text-sm cursor-pointer"
        >
          View Businesses Directory
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card-3d p-4 rounded-xl flex items-start space-x-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono">Unique Matches</div>
            <div className="text-xl font-bold text-white font-mono">{report.total_verified}</div>
          </div>
        </div>
        
        <div className="card-3d p-4 rounded-xl flex items-start space-x-3">
          <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400">
            <Trash2 className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono">Duplicates Merged</div>
            <div className="text-xl font-bold text-violet-400 font-mono">{report.duplicates_removed}</div>
          </div>
        </div>

        <div className="card-3d p-4 rounded-xl flex items-start space-x-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono">Scrape Duration</div>
            <div className="text-xl font-bold text-emerald-400 font-mono flex items-baseline space-x-0.5">
              <span>{report.duration.toFixed(1)}</span>
              <span className="text-xs font-normal text-slate-500 font-sans">s</span>
            </div>
          </div>
        </div>

        <div className="card-3d p-4 rounded-xl flex items-start space-x-3">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <Globe className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-mono">Sources Queried</div>
            <div className="text-xl font-bold text-white font-mono">{report.sources_used}</div>
          </div>
        </div>
      </div>

      {/* Visual Analytics Charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Field Coverage Gauge Chart */}
        <div className="card-3d p-5 rounded-2xl flex flex-col h-80">
          <h2 className="text-sm font-bold text-slate-400 uppercase font-mono tracking-wider mb-4">
            Field Verification Coverage
          </h2>
          <div className="flex-1 min-h-0 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart 
                cx="50%" 
                cy="50%" 
                innerRadius="30%" 
                outerRadius="100%" 
                barSize={15} 
                data={coverageData}
              >
                <RadialBar
                  label={{ position: 'insideStart', fill: '#fff', fontSize: 10 }}
                  background
                  dataKey="percentage"
                />
                <Legend 
                  iconSize={10} 
                  layout="horizontal" 
                  verticalAlign="bottom" 
                  align="center"
                  wrapperStyle={{ fontSize: 11 }}
                />
                <Tooltip formatter={(value) => `${value}%`} />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Verification score distribution */}
        <div className="card-3d p-5 rounded-2xl flex flex-col h-80">
          <h2 className="text-sm font-bold text-slate-400 uppercase font-mono tracking-wider mb-4">
            Verification Quality Distribution
          </h2>
          <div className="flex-1 min-h-0 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={distributionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {distributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value} profiles`} />
                <Legend iconSize={10} layout="horizontal" verticalAlign="bottom" align="center" wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Source Contribution Chart */}
        <div className="card-3d p-5 rounded-2xl flex flex-col h-80">
          <h2 className="text-sm font-bold text-slate-400 uppercase font-mono tracking-wider mb-4">
            Profile Sourcing Share
          </h2>
          <div className="flex-1 min-h-0 relative">
            {sourceData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sourceData} margin={{ bottom: 15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500 text-xs">No source details loaded</div>
            )}
          </div>
        </div>
      </div>

      {/* Structured Report Summary Content */}
      <div className="card-3d rounded-2xl overflow-hidden shadow-2xl p-6 md:p-8 space-y-6">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-4">
          <FileText className="h-5 w-5 text-indigo-400" />
          <h2 className="text-lg font-bold text-white uppercase font-mono tracking-wider">Executive Report Summary</h2>
        </div>
        
        {/* Markdown-like formatting layout */}
        <div 
          className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed space-y-4"
          dangerouslySetInnerHTML={{ __html: formatReportMarkdown(report.report_markdown) }}
        />
      </div>
    </div>
  );
}
