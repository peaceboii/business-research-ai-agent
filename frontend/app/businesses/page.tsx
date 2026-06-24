"use client";

import { useEffect, useState, useRef } from "react";
import { 
  Search, SlidersHorizontal, ArrowUpDown, ChevronLeft, ChevronRight, 
  Download, Upload, ShieldCheck, Mail, Globe, Phone, MapPin, X, 
  AlertTriangle, Check, RefreshCw, Star, Clock, FileText, Award, BadgeCheck 
} from "lucide-react";

export default function BusinessesPage() {
  // API base state to prevent SSR hydration mismatch
  const [apiBase, setApiBase] = useState("http://localhost:8000/api");

  useEffect(() => {
    setApiBase(`http://${window.location.hostname}:8000/api`);
  }, []);

  // Query state
  const [search, setSearch] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [sortBy, setSortBy] = useState("verification_score");
  const [businesses, setBusinesses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Pagination
  const [page, setPage] = useState(1);
  const limit = 15;

  // Selected Business for Drawer
  const [selectedBiz, setSelectedBiz] = useState<any | null>(null);
  const [selectedBizConflicts, setSelectedBizConflicts] = useState<any[]>([]);
  const [bizLoading, setBizLoading] = useState(false);
  const [conflictResolving, setConflictResolving] = useState<number | null>(null);

  // Upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchBusinesses();
  }, [search, minScore, sortBy, page]);

  useEffect(() => {
    if (selectedBiz) {
      fetchConflicts(selectedBiz.id);
    }
  }, [selectedBiz]);

  const fetchBusinesses = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      let url = `${apiBase}/businesses?skip=${skip}&limit=${limit}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      if (minScore > 0) url += `&min_verification_score=${minScore}`;
      
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setBusinesses(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchConflicts = async (bizId: number) => {
    try {
      // List all conflicts
      const res = await fetch(`${apiBase}/conflicts?resolved=false`);
      if (res.ok) {
        const data = await res.json();
        // Filter to conflicts for the selected business
        const bizConflicts = data.filter((c: any) => c.business_id === bizId);
        setSelectedBizConflicts(bizConflicts);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const resolveConflict = async (conflictId: number, resolvedValue: string) => {
    setConflictResolving(conflictId);
    try {
      const res = await fetch(`${apiBase}/conflicts/${conflictId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolved_value: resolvedValue })
      });
      if (res.ok) {
        // Refresh details
        if (selectedBiz) {
          const bizRes = await fetch(`${apiBase}/businesses/${selectedBiz.id}`);
          if (bizRes.ok) {
            const updatedBiz = await bizRes.json();
            setSelectedBiz(updatedBiz);
          }
          await fetchConflicts(selectedBiz.id);
          // Refresh lists
          await fetchBusinesses();
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setConflictResolving(null);
    }
  };

  // CSV Import handling
  const handleCSVImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${apiBase}/businesses/import/csv`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        alert("Businesses imported successfully!");
        fetchBusinesses();
      } else {
        const err = await res.json();
        alert(`Failed to import: ${err.detail}`);
      }
    } catch (e) {
      console.error(e);
      alert("Error importing CSV file.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6">
      {/* Directory Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Businesses Directory</h1>
          <p className="text-slate-400 text-sm mt-1">Browse, inspect, and export verified research records.</p>
        </div>
        
        {/* Import/Export buttons */}
        <div className="flex space-x-2">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleCSVImport} 
            accept=".csv" 
            className="hidden" 
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-semibold px-4 py-2 rounded-xl transition-all flex items-center space-x-2 cursor-pointer text-sm"
          >
            {uploading ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            <span>{uploading ? "Importing..." : "Import CSV"}</span>
          </button>
          
          <a
            href={`${apiBase}/businesses/export/csv`}
            className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-semibold px-4 py-2 rounded-xl transition-all flex items-center space-x-2 text-sm"
          >
            <Download className="h-4 w-4" />
            <span>Export CSV</span>
          </a>
          <a
            href={`${apiBase}/businesses/export/json`}
            className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-semibold px-4 py-2 rounded-xl transition-all flex items-center space-x-2 text-sm"
          >
            <Download className="h-4 w-4" />
            <span>Export JSON</span>
          </a>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="card-3d p-4 rounded-2xl flex flex-col md:flex-row gap-4 items-center">
        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3.5 top-2.5 h-4.5 w-4.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search name, service, address..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-950 border border-slate-800 text-white rounded-xl py-2 pl-10 pr-4 focus:outline-none focus:border-indigo-500 text-sm"
          />
        </div>

        {/* Verification Score Filter */}
        <div className="flex items-center space-x-3 w-full md:w-auto">
          <SlidersHorizontal className="h-4 w-4 text-slate-500" />
          <span className="text-xs text-slate-400 font-medium">Min Score: {minScore}</span>
          <input
            type="range"
            min="0"
            max="100"
            step="10"
            value={minScore}
            onChange={(e) => {
              setMinScore(parseInt(e.target.value));
              setPage(1);
            }}
            className="accent-indigo-500 h-1.5 bg-slate-850 rounded-lg cursor-pointer flex-1 md:w-36"
          />
        </div>
      </div>

      {/* Main Table */}
      <div className="card-3d rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/40 text-xs text-slate-400 uppercase font-semibold font-mono">
                <th className="px-6 py-4">Business Name</th>
                <th className="px-6 py-4">Rating</th>
                <th className="px-6 py-4">Verification</th>
                <th className="px-6 py-4">Contact Info</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm">
              {loading ? (
                [1, 2, 3, 4, 5].map((i) => (
                  <tr key={i} className="animate-pulse">
                    <td colSpan={5} className="px-6 py-6"><div className="h-4 bg-slate-800 rounded w-1/3"></div></td>
                  </tr>
                ))
              ) : businesses.length > 0 ? (
                businesses.map((biz) => (
                  <tr 
                    key={biz.id} 
                    onClick={() => setSelectedBiz(biz)}
                    className="hover:bg-slate-900/20 transition-colors cursor-pointer group"
                  >
                    <td className="px-6 py-4">
                      <div className="font-semibold text-white group-hover:text-indigo-400 transition-colors">{biz.business_name}</div>
                      <div className="text-slate-400 text-xs mt-0.5 max-w-xs truncate">{biz.address}</div>
                    </td>
                    <td className="px-6 py-4">
                      {biz.rating ? (
                        <div className="flex items-center space-x-1">
                          <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                          <span className="font-mono text-white">{biz.rating}</span>
                          <span className="text-xs text-slate-500">({biz.review_count})</span>
                        </div>
                      ) : (
                        <span className="text-slate-500 font-mono text-xs">No reviews</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="inline-flex items-center space-x-1 bg-slate-950 border border-slate-800 px-2 py-1 rounded font-mono text-xs text-slate-300">
                        <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
                        <span>{biz.verification_score}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 space-y-1">
                      {biz.phone && (
                        <div className="text-xs text-slate-400 flex items-center space-x-1 font-mono">
                          <Phone className="h-3 w-3 text-slate-600" />
                          <span>{biz.phone}</span>
                        </div>
                      )}
                      {biz.website && (
                        <div className="text-xs text-indigo-400 flex items-center space-x-1 font-mono truncate max-w-xs">
                          <Globe className="h-3 w-3 text-indigo-500/60" />
                          <span>{biz.website.replace("https://", "").replace("http://", "").split("/")[0]}</span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedBiz(biz);
                        }}
                        className="text-xs text-indigo-400 group-hover:text-indigo-300 font-semibold cursor-pointer"
                      >
                        Inspect Details
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-slate-500">
                    No businesses found matching filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="border-t border-slate-800 px-6 py-4 flex items-center justify-between bg-slate-900/20 text-xs">
          <div className="text-slate-500">Showing page {page}</div>
          <div className="flex space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="bg-slate-950 border border-slate-800 hover:bg-slate-800 p-2 rounded-lg text-slate-400 hover:text-white cursor-pointer disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={businesses.length < limit}
              className="bg-slate-950 border border-slate-800 hover:bg-slate-800 p-2 rounded-lg text-slate-400 hover:text-white cursor-pointer disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Slide-over Side Drawer Detail Panel */}
      {selectedBiz && (
        <div 
          onClick={() => setSelectedBiz(null)}
          className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity cursor-pointer"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl bg-slate-950 border-l border-slate-800 h-full flex flex-col shadow-2xl relative animate-in slide-in-from-right duration-300 cursor-default"
          >
            {/* Drawer Header */}
            <div className="p-6 border-b border-slate-800 flex justify-between items-start bg-slate-900/40">
              <div className="space-y-1 max-w-[85%]">
                <h2 className="text-xl font-bold text-white">{selectedBiz.business_name}</h2>
                <div className="flex items-center space-x-3 text-xs">
                  <div className="inline-flex items-center space-x-1 text-slate-300 font-mono">
                    <ShieldCheck className="h-4 w-4 text-indigo-400" />
                    <span className="font-bold text-white">{selectedBiz.verification_score}</span>
                    <span className="text-slate-500">/ 100 verification score</span>
                  </div>
                  {selectedBiz.license_information && (
                    <span className="text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded font-mono">
                      License: {selectedBiz.license_information}
                    </span>
                  )}
                </div>
              </div>
              <button 
                onClick={() => setSelectedBiz(null)}
                className="text-slate-500 hover:text-white p-1 hover:bg-slate-800/60 rounded-lg cursor-pointer transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Drawer Body Scroll */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Conflict Warning banner */}
              {selectedBizConflicts.length > 0 && (
                <div className="border border-amber-500/20 bg-amber-500/5 p-4 rounded-xl space-y-3">
                  <div className="flex items-center space-x-2 text-amber-400 font-semibold text-xs uppercase font-mono">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Scraping Conflict Detected</span>
                  </div>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    Discovery adapters fetched mismatched fields. Select a verified value below to manually resolve and finalize the business profile:
                  </p>

                  <div className="space-y-3 pt-1">
                    {selectedBizConflicts.map((conf) => (
                      <div key={conf.id} className="border border-slate-800 bg-slate-950 p-3 rounded-lg space-y-2">
                        <div className="text-[11px] text-slate-400 font-semibold font-mono uppercase">
                          Field: {conf.field_name}
                        </div>
                        <div className="flex flex-col gap-1.5">
                          {conf.conflicting_values.map((val: string) => (
                            <button
                              key={val}
                              disabled={conflictResolving === conf.id}
                              onClick={() => resolveConflict(conf.id, val)}
                              className="flex items-center justify-between text-xs bg-slate-900 border border-slate-800 hover:border-indigo-500 text-slate-300 hover:text-white px-3 py-2 rounded-lg text-left transition-colors cursor-pointer group disabled:opacity-50"
                            >
                              <span className="font-mono">{val}</span>
                              <span className="text-[10px] text-indigo-400 group-hover:text-indigo-300 flex items-center space-x-1">
                                <span>Choose value</span>
                                <Check className="h-3 w-3" />
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Standard contact details */}
              <div className="bg-slate-900/20 border border-slate-800 p-4 rounded-xl space-y-3 text-sm">
                <h3 className="font-bold text-white text-xs uppercase font-mono tracking-wider text-slate-400">Contact Details</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {selectedBiz.phone && (
                    <div className="flex items-center space-x-2 text-slate-300">
                      <Phone className="h-4 w-4 text-slate-500" />
                      <span className="font-mono">{selectedBiz.phone}</span>
                    </div>
                  )}
                  {selectedBiz.email && (
                    <div className="flex items-center space-x-2 text-slate-300 truncate">
                      <Mail className="h-4 w-4 text-slate-500" />
                      <span>{selectedBiz.email}</span>
                    </div>
                  )}
                  {selectedBiz.website && (
                    <div className="flex items-center space-x-2 text-indigo-400 truncate">
                      <Globe className="h-4 w-4 text-indigo-500" />
                      <a href={selectedBiz.website} target="_blank" rel="noreferrer" className="hover:underline">
                        {selectedBiz.website}
                      </a>
                    </div>
                  )}
                  {selectedBiz.address && (
                    <div className="flex items-start space-x-2 text-slate-300 md:col-span-2">
                      <MapPin className="h-4 w-4 text-slate-500 mt-0.5" />
                      <span>{selectedBiz.address}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Services & specialties */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <h3 className="font-bold text-xs uppercase font-mono tracking-wider text-slate-400">Services & Specialities</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedBiz.services?.length > 0 ? (
                      selectedBiz.services.map((s: string) => (
                        <span key={s} className="bg-slate-900 border border-slate-800 text-slate-300 text-xs px-2.5 py-1 rounded-lg">
                          {s}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500 italic">No services listed</span>
                    )}
                  </div>
                </div>
                
                {selectedBiz.certifications?.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-bold text-xs uppercase font-mono tracking-wider text-slate-400">Certifications</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedBiz.certifications.map((c: string) => (
                        <span key={c} className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs px-2.5 py-1 rounded-lg flex items-center space-x-1">
                          <BadgeCheck className="h-3.5 w-3.5 text-emerald-400" />
                          <span>{c}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedBiz.awards?.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-bold text-xs uppercase font-mono tracking-wider text-slate-400">Awards & Accolades</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedBiz.awards.map((a: string) => (
                        <span key={a} className="bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs px-2.5 py-1 rounded-lg flex items-center space-x-1">
                          <Award className="h-3.5 w-3.5 text-amber-400" />
                          <span>{a}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Working Hours */}
              {selectedBiz.working_hours && Object.keys(selectedBiz.working_hours).length > 0 && (
                <div className="bg-slate-900/10 border border-slate-800 p-4 rounded-xl space-y-2">
                  <h3 className="font-bold text-xs uppercase font-mono tracking-wider text-slate-400 flex items-center space-x-1">
                    <Clock className="h-4 w-4 text-slate-500" />
                    <span>Working Hours</span>
                  </h3>
                  <div className="divide-y divide-slate-800/40 text-xs">
                    {Object.entries(selectedBiz.working_hours).map(([day, hours]: any) => (
                      <div key={day} className="flex justify-between py-2 font-mono">
                        <span className="text-slate-400 font-semibold">{day}</span>
                        <span className="text-white">{hours}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Source breakdown */}
              {selectedBiz.source_urls && Object.keys(selectedBiz.source_urls).length > 0 && (
                <div className="bg-slate-900/10 border border-slate-800 p-4 rounded-xl space-y-2">
                  <h3 className="font-bold text-xs uppercase font-mono tracking-wider text-slate-400 flex items-center space-x-1">
                    <FileText className="h-4 w-4 text-slate-500" />
                    <span>Verification Audit Sources</span>
                  </h3>
                  <div className="divide-y divide-slate-800/40 text-xs">
                    {Object.entries(selectedBiz.source_urls).map(([field, urls]: any) => (
                      <div key={field} className="py-2.5 space-y-1">
                        <span className="text-slate-400 font-semibold capitalize font-mono text-[11px]">{field} verified in:</span>
                        <div className="flex flex-wrap gap-1">
                          {urls.map((url: string, idx: number) => (
                            <a
                              key={idx}
                              href={url.startsWith("http") ? url : undefined}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[10px] bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-indigo-500/30 text-indigo-400 px-2 py-0.5 rounded font-mono truncate max-w-xs block cursor-pointer"
                            >
                              {url.replace("https://", "").replace("http://", "").split("/")[0]}
                            </a>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
