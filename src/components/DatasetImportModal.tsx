'use client';

import React, { useState } from 'react';
import { 
  Database, 
  X, 
  ExternalLink, 
  Loader2, 
  CheckCircle2, 
  AlertCircle, 
  DownloadCloud, 
  Sparkles,
  ChevronDown,
  ChevronUp,
  Tag,
  Clock,
  Layers
} from 'lucide-react';
import { DatasetPreviewItem, DatasetImportResult } from '@/lib/types';
import { PriorityBadge, CategoryBadge, StatusBadge } from '@/components/Badges';

interface DatasetImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess: () => void;
}

export function DatasetImportModal({ isOpen, onClose, onImportSuccess }: DatasetImportModalProps) {
  const [importCount, setImportCount] = useState<number>(25);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [importing, setImporting] = useState(false);
  const [previewItems, setPreviewItems] = useState<DatasetPreviewItem[] | null>(null);
  const [totalAvailable, setTotalAvailable] = useState<number | null>(null);
  const [showPreviewTable, setShowPreviewTable] = useState(false);
  const [importResult, setImportResult] = useState<DatasetImportResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFetchPreview = async () => {
    try {
      setLoadingPreview(true);
      setErrorMessage(null);
      const res = await fetch('/api/dataset/preview?limit=6');
      const data = await res.json();
      if (data.success) {
        setPreviewItems(data.data.preview);
        setTotalAvailable(data.data.totalAvailable);
        setShowPreviewTable(true);
      } else {
        setErrorMessage(data.error || 'Failed to fetch dataset preview');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error fetching dataset preview');
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleRunImport = async () => {
    try {
      setImporting(true);
      setErrorMessage(null);
      setImportResult(null);

      const res = await fetch('/api/dataset/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: importCount })
      });

      const data = await res.json();
      if (data.success) {
        setImportResult(data.data);
        onImportSuccess();
      } else {
        setErrorMessage(data.error || 'Dataset import failed');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error during dataset import');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
              <DownloadCloud className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <span>Import Help Desk Dataset</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Hugging Face 🤖
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Populate realistic support tickets from the verified industry benchmark dataset
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Dataset Info Card */}
          <div className="p-4 rounded-2xl bg-slate-800/40 border border-slate-700/50 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Dataset Source</p>
                <p className="text-sm font-semibold text-white">mindweave/help-desk-tickets</p>
              </div>
              <a
                href="https://huggingface.co/datasets/mindweave/help-desk-tickets"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium"
              >
                <span>View on Hugging Face</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Standardized IT service management dataset containing realistic support tickets across departments (Finance, HR, Operations, Sales), mapped to priorities (P1–P4), incident categories, and verified resolution logs.
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
                <Layers className="w-3 h-3 text-indigo-400" />
                <span>3,000+ benchmark tickets</span>
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
                <Sparkles className="w-3 h-3 text-cyan-400" />
                <span>Auto-Semantic Embedding</span>
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span>Duplicate Prevention</span>
              </span>
            </div>
          </div>

          {/* Import Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                Number of Tickets to Import
              </label>
              <select
                value={importCount}
                onChange={(e) => setImportCount(Number(e.target.value))}
                disabled={importing}
                className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value={10}>10 Tickets (Fast Test)</option>
                <option value={25}>25 Tickets (Recommended)</option>
                <option value={50}>50 Tickets</option>
                <option value={100}>100 Tickets (Full Batch)</option>
              </select>
              <p className="text-[11px] text-slate-400">
                Existing tickets will not be duplicated. Embeddings will be automatically indexed.
              </p>
            </div>

            <div className="space-y-2 flex flex-col justify-end">
              <button
                type="button"
                onClick={handleFetchPreview}
                disabled={loadingPreview || importing}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-sm font-semibold transition-all disabled:opacity-50"
              >
                {loadingPreview ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                    <span>Fetching Schema...</span>
                  </>
                ) : (
                  <>
                    <Database className="w-4 h-4 text-cyan-400" />
                    <span>{showPreviewTable ? 'Refresh Preview' : 'Preview Dataset'}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Preview Section */}
          {showPreviewTable && previewItems && (
            <div className="space-y-2 border border-slate-800 rounded-2xl p-4 bg-slate-950/60">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <span>Sample Record Mapping</span>
                  {totalAvailable && (
                    <span className="text-slate-400 font-normal">({totalAvailable} available)</span>
                  )}
                </span>
                <button
                  type="button"
                  onClick={() => setShowPreviewTable(false)}
                  className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1"
                >
                  <span>Hide</span>
                  <ChevronUp className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2 font-semibold">Incident Title</th>
                      <th className="pb-2 font-semibold">Category</th>
                      <th className="pb-2 font-semibold">Priority</th>
                      <th className="pb-2 font-semibold">Status</th>
                      <th className="pb-2 font-semibold">Dept</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {previewItems.map((item) => (
                      <tr key={item.external_id} className="hover:bg-slate-900/50">
                        <td className="py-2.5 pr-2 font-medium text-white max-w-[240px] truncate" title={item.title}>
                          {item.title}
                        </td>
                        <td className="py-2.5 pr-2">
                          <CategoryBadge category={item.category} />
                        </td>
                        <td className="py-2.5 pr-2">
                          <PriorityBadge priority={item.priority} />
                        </td>
                        <td className="py-2.5 pr-2">
                          <StatusBadge status={item.status} />
                        </td>
                        <td className="py-2.5 text-slate-400">{item.department || 'IT'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Success Summary */}
          {importResult && (
            <div className="p-4 rounded-2xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 text-xs space-y-2">
              <div className="flex items-center gap-2 font-semibold text-sm text-emerald-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Import Completed Successfully! 🎉</span>
              </div>
              <p>
                Processed <strong className="text-white">{importResult.totalProcessed}</strong> records:
                {' '}Successfully added <strong className="text-white">{importResult.importedCount}</strong> new incidents,
                and skipped <strong className="text-white">{importResult.skippedCount}</strong> existing duplicates.
              </p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-800 bg-slate-900/80">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 text-sm font-medium transition-colors"
          >
            Close
          </button>

          <button
            type="button"
            onClick={handleRunImport}
            disabled={importing}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
          >
            {importing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Importing {importCount} Tickets...</span>
              </>
            ) : (
              <>
                <DownloadCloud className="w-4 h-4" />
                <span>Import {importCount} Tickets</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
