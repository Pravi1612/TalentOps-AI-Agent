import { useEffect, useState } from 'react';
import { getStatus, getResults } from '../api/client.js';

const STEP_LABELS = {
  1: 'Ingestion (resumes parsed)',
  2: 'Profile extraction',
  3: 'Fitment analysis',
  4: 'Interview question banks',
  5: 'Panelist feedback templates',
  6: 'Comparison + compliance + briefing',
};

export default function ProcessingView({ sessionId, onComplete, onError }) {
  const [progress, setProgress] = useState({});
  const [status, setStatus] = useState('processing');

  useEffect(() => {
    let cancelled = false;
    let timer;

    const poll = async () => {
      try {
        const data = await getStatus(sessionId);
        if (cancelled) return;
        setProgress(data.step_progress || {});
        setStatus(data.status);
        if (data.status === 'completed') {
          const results = await getResults(sessionId);
          if (!cancelled) onComplete?.(results);
          return;
        }
        if (data.status === 'failed') {
          onError?.(data.error || 'Pipeline failed');
          return;
        }
        timer = setTimeout(poll, 2000);
      } catch (err) {
        if (!cancelled) onError?.(err?.response?.data?.detail || err.message);
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId]);

  return (
    <section className="bg-white rounded shadow-sm p-6 border border-slate-200">
      <h2 className="text-lg font-semibold mb-3">Processing batch…</h2>
      <p className="text-xs text-slate-500 mb-4">Session {sessionId} — status: {status}</p>
      <ul className="space-y-2">
        {Object.entries(STEP_LABELS).map(([step, label]) => {
          const state = progress[step] || 'pending';
          const icon = state === 'completed' ? '✓' : state === 'in_progress' ? '…' : '○';
          const color =
            state === 'completed'
              ? 'text-green-600'
              : state === 'in_progress'
                ? 'text-blue-600'
                : 'text-slate-400';
          return (
            <li key={step} className={`flex items-center gap-2 text-sm ${color}`}>
              <span className="font-mono w-4">{icon}</span>
              <span>Step {step} — {label}</span>
              <span className="text-xs ml-auto">{state}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
