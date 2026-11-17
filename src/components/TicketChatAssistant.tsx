'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  Loader2, 
  Trash2, 
  AlertCircle, 
  User, 
  HelpCircle,
  CheckCircle2,
  Cpu
} from 'lucide-react';
import { TicketChatMessage } from '@/lib/types';

interface TicketChatAssistantProps {
  ticketId: number;
  ticketTitle: string;
}

const SUGGESTED_PROMPTS = [
  'What logs should I check? 🔍',
  'Explain root cause in simpler terms 💡',
  'Why is this issue happening? ❓',
  'What if the solution does not work? 🔄'
];

export function TicketChatAssistant({ ticketId, ticketTitle }: TicketChatAssistantProps) {
  const [messages, setMessages] = useState<TicketChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [confirmClear, setConfirmClear] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchMessages = async () => {
    try {
      setInitialLoading(true);
      const res = await fetch(`/api/ai/chat?ticketId=${ticketId}`);
      const data = await res.json();
      if (data.success) {
        setMessages(data.data || []);
      }
    } catch (err) {
      console.error('Failed to load chat history:', err);
    } finally {
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [ticketId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || loading) return;

    setError(null);
    setInputMessage('');

    // Optimistically add user message to UI
    const tempUserMsg: TicketChatMessage = {
      id: Date.now(),
      ticket_id: ticketId,
      sender: 'user',
      message: text,
      is_fallback: false,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setLoading(true);

    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticketId, message: text })
      });

      const data = await res.json();
      if (data.success && data.data) {
        // Replace temp messages with actual persisted response
        setMessages(prev => [
          ...prev.filter(m => m.id !== tempUserMsg.id),
          data.data.userMessage,
          data.data.assistantMessage
        ]);
      } else {
        setError(data.error || 'Failed to send message');
      }
    } catch (err: any) {
      setError(err.message || 'Error communicating with AI assistant');
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      const res = await fetch(`/api/ai/chat?ticketId=${ticketId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (data.success) {
        setMessages([]);
        setConfirmClear(false);
      }
    } catch (err) {
      console.error('Failed to clear chat:', err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-col h-[650px] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center relative">
            <Bot className="w-5 h-5" />
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-slate-900 animate-pulse" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Conversational AI Assistant</span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 font-medium">
                Incident Copilot 🤖
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Context-grounded triage assistant for Ticket #{ticketId}
            </p>
          </div>
        </div>

        {/* Clear History Button / Confirm */}
        <div className="flex items-center gap-2">
          {confirmClear ? (
            <div className="flex items-center gap-1.5 animate-in fade-in duration-150">
              <span className="text-xs text-rose-300 font-medium">Clear history?</span>
              <button
                onClick={handleClearHistory}
                className="px-2 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
              >
                Yes, Clear
              </button>
              <button
                onClick={() => setConfirmClear(false)}
                className="px-2 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs"
              >
                Cancel
              </button>
            </div>
          ) : (
            messages.length > 0 && (
              <button
                onClick={() => setConfirmClear(true)}
                className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 transition-colors"
                title="Clear conversation history"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )
          )}
        </div>
      </div>

      {/* Suggested Prompts Pill Bar */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs">
        <span className="text-slate-500 shrink-0 flex items-center gap-1 font-medium">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          <span>Suggestions:</span>
        </span>
        {SUGGESTED_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSendMessage(prompt)}
            disabled={loading}
            className="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-indigo-600/20 text-slate-300 hover:text-indigo-300 border border-slate-700/60 hover:border-indigo-500/40 transition-all text-[11px] disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {initialLoading ? (
          <div className="h-full flex flex-col items-center justify-center space-y-2 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
            <p className="text-xs">Loading incident conversation history...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center">
              <Bot className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-white">How can I help with this incident?</p>
              <p className="text-xs text-slate-400 max-w-sm">
                I have full context of <strong>&ldquo;{ticketTitle}&rdquo;</strong>, including root cause, relevant runbooks, and historical resolutions.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 space-y-1.5 shadow-sm text-xs leading-relaxed ${
                    isUser
                      ? 'bg-indigo-600 text-white rounded-tr-sm'
                      : 'bg-slate-800/90 text-slate-200 border border-slate-700/70 rounded-tl-sm'
                  }`}
                >
                  {/* Sender label & Fallback flag */}
                  <div className="flex items-center justify-between gap-2 text-[10px] opacity-75">
                    <span className="font-semibold uppercase tracking-wider">
                      {isUser ? 'Support Engineer' : 'AI Assistant'}
                    </span>
                    {!isUser && msg.is_fallback && (
                      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
                        <Cpu className="w-2.5 h-2.5" />
                        <span>Heuristic Engine</span>
                      </span>
                    )}
                  </div>

                  {/* Message Content */}
                  <div className="whitespace-pre-wrap font-sans">
                    {msg.message}
                  </div>
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 border border-slate-700 flex items-center justify-center shrink-0 mt-1">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Loading Bubble */}
        {loading && (
          <div className="flex gap-3 justify-start animate-in fade-in duration-150">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-slate-800/90 border border-slate-700/70 rounded-2xl rounded-tl-sm p-3.5 flex items-center gap-2 text-xs text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Analyzing incident context and formulating diagnosis...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="pt-2 border-t border-slate-800/80">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a technical question about this incident..."
            disabled={loading}
            className="flex-1 bg-slate-800/80 border border-slate-700 rounded-2xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            className="p-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-all hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
            title="Send Message"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
