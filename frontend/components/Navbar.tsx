import Link from "next/link";
import { Search, Database, FileText, Activity } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <Search className="h-5 w-5 text-white" />
              </div>
              <span className="font-bold text-xl bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
                Research.AI
              </span>
            </Link>
            <div className="hidden md:block ml-10">
              <div className="flex space-x-4">
                <Link
                  href="/"
                  className="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-1 hover:bg-slate-800/40"
                >
                  <Activity className="h-4 w-4" />
                  <span>Dashboard</span>
                </Link>
                <Link
                  href="/businesses"
                  className="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center space-x-1 hover:bg-slate-800/40"
                >
                  <Database className="h-4 w-4" />
                  <span>Businesses</span>
                </Link>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-slate-400 font-mono">Agent Status: Active</span>
          </div>
        </div>
      </div>
    </nav>
  );
}
