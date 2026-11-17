'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Sparkles, 
  ExternalLink, 
  FileText, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp, 
  Copy, 
  Check, 
  AlertCircle,
  Loader2,
  RefreshCw,
  GitBranch
} from 'lucide-react';
import { SimilarIncident } from '@/lib/types';
import { PriorityBadge, StatusBadge, CategoryBadge } from '@/components/Badges';

interface SimilarIncidentsSectionProps {
  ticketId: number;
  onApplyResolution?: (resolutionText: string) => void;
}

export function SimilarIncidentsSection({ ticketId, onApplyResolution }: SimilarIncidentsSectionProps) {
  const [similarIncidents, setSimilarIncidents] = useState<SimilarIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedResolutionId, setExpandedResolutionId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const fetchSimilar = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/tickets/${ticketId}/similar?limit=4`);
      const data = await res.json();
      if (data.success) {
        setSimilarIncidents(data.data || []);
      }
    } catch (err) {
      console.error('Failed to load similar incidents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSimilar();
  }, [ticketId]);

  const handleCopy = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getScoreBadgeClass = (score: number) => {
    if (score >= 80) return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
    if (score >= 60) return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    if (score >= 40) return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';
    return 'bg-slate-700/50 text-slate-300 border-slate-600/40';
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-5">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🔍 Similar Incidents</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-medium">
                AI Semantic Cosine
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Contextually similar historical tickets & reusable previous resolutions
            </p>
          </div>
        </div>

        <button
          onClick={fetchSimilar}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-700/60 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
          <p className="text-xs text-slate-400">Comparing semantic embeddings against ticket history...</p>
        </div>
      ) : similarIncidents.length === 0 ? (
        <div className="py-8 text-center bg-slate-950/40 rounded-2xl border border-slate-800/60 space-y-2">
          <p className="text-sm font-semibold text-slate-300">No Similar Incidents Found</p>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            This incident appears unique or no historical tickets have exceeded the semantic similarity threshold.
          </p>
        </div>
      ) : (
        <div className="space-y-3.5">
          {similarIncidents.map((incident) => {
            const isExpanded = expandedResolutionId === incident.id;
            return (
              <div 
                key={incident.id}
                className="p-4 rounded-2xl bg-slate-800/40 border border-slate-800 hover:border-slate-700/80 transition-all space-y-3"
              >
                {/* Header row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-slate-400">
                      #{incident.id}
                    </span>
                    <Link
                      href={`/tickets/${incident.id}`}
                      target="_blank"
                      className="text-sm font-semibold text-white hover:text-cyan-400 transition-colors flex items-center gap-1.5 group"
                    >
                      <span className="line-clamp-1">{incident.title}</span>
                      <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 shrink-0" />
                    </Link>
                  </div>

                  {/* Similarity score badge */}
                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${getScoreBadgeClass(incident.similarityScore)}`}>
                      {incident.similarityScore}% Match
                    </span>
                    <PriorityBadge priority={incident.priority} />
                    <StatusBadge status={incident.status} />
                  </div>
                </div>

                {/* Meta & actions row */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/60 text-xs">
                  <div className="flex items-center gap-2">
                    <CategoryBadge category={incident.category} />
                    {incident.hasResolution && (
                      <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Resolved Guide Available</span>
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {incident.hasResolution && (
                      <button
                        onClick={() => setExpandedResolutionId(isExpanded ? null : incident.id)}
                        className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 font-medium py-1 px-2 rounded-lg hover:bg-cyan-500/10 transition-colors"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>{isExpanded ? 'Hide Resolution' : 'View Previous Resolution'}</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    )}

                    <Link
                      href={`/tickets/${incident.id}`}
                      className="text-slate-400 hover:text-slate-200 font-medium py-1 px-2 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                      View Incident ➔
                    </Link>
                  </div>
                </div>

                {/* Resolution Drawer */}
                {isExpanded && incident.resolution && (
                  <div className="mt-3 p-3.5 rounded-xl bg-slate-950/80 border border-slate-700/60 space-y-2.5 animate-in fade-in duration-150">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Historical Resolution Notes from #{incident.id}</span>
                      </span>

                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleCopy(incident.id, incident.resolution!)}
                          className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                        >
                          {copiedId === incident.id ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy Notes</span>
                            </>
                          )}
                        </button>

                        {onApplyResolution && (
                          <button
                            onClick={() => onApplyResolution(incident.resolution!)}
                            className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow transition-colors"
                          >
                            <GitBranch className="w-3 h-3" />
                            <span>Reuse in this Ticket</span>
                          </button>
                        )}
                      </div>
                    </div>

                    <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                      {incident.resolution}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
