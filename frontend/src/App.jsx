import { useEffect, useState } from 'react';
import UploadPanel from './components/UploadPanel.jsx';
import ProcessingView from './components/ProcessingView.jsx';
import ComparisonTable from './components/ComparisonTable.jsx';
import ComplianceReport from './components/ComplianceReport.jsx';
import CandidateCard from './components/CandidateCard.jsx';
import QuestionBankView from './components/QuestionBankView.jsx';
import { getHealth } from './api/client.js';

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ provider: 'unknown' }));
  }, []);

  const reset = () => {
    setSessionId(null);
    setResults(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-slate-900 text-white px-6 py-4 shadow flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">TalentOps Agent</h1>
          <p className="text-xs text-slate-300">
            AI-assisted resume screening — recruiter review required.
          </p>
        </div>
        {health?.provider === 'mock' && (
          <span className="text-xs font-semibold uppercase tracking-wide bg-amber-400 text-slate-900 px-2 py-1 rounded">
            Mock mode
          </span>
        )}
      </header>

      <main className="max-w-6xl mx-auto p-6 space-y-6">
        {error && (
          <div className="bg-red-100 border border-red-300 text-red-800 p-3 rounded">
            {String(error)}
          </div>
        )}

        {!sessionId && !results && (
          <UploadPanel onStart={setSessionId} onError={setError} />
        )}

        {sessionId && !results && (
          <ProcessingView
            sessionId={sessionId}
            onComplete={setResults}
            onError={setError}
          />
        )}

        {results && (
          <div className="space-y-6">
            <button
              onClick={reset}
              className="text-sm text-blue-600 hover:underline"
            >
              ← Start a new batch
            </button>
            <ComparisonTable comparison={results.comparison} briefing={results.panel_briefing} />
            <ComplianceReport report={results.compliance_report} />
            <section>
              <h2 className="text-lg font-semibold mb-2">Candidates</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {results.candidates.map((c, i) => (
                  <CandidateCard key={i} bundle={c} />
                ))}
              </div>
            </section>
            <QuestionBankView candidates={results.candidates} />
            <Downloads urls={results.artifact_urls} />
          </div>
        )}
      </main>
    </div>
  );
}

function Downloads({ urls }) {
  if (!urls) return null;
  return (
    <section className="bg-white border rounded p-4 shadow-sm">
      <h2 className="font-semibold mb-2">Generated artifacts</h2>
      <ul className="list-disc pl-5 text-sm space-y-1">
        {urls.feedback_templates_docx?.map((u, i) => (
          <li key={i}>
            <a className="text-blue-600 hover:underline" href={u} target="_blank" rel="noreferrer">
              Panelist feedback template {i + 1} (.docx)
            </a>
          </li>
        ))}
        {urls.comparison_xlsx && (
          <li>
            <a className="text-blue-600 hover:underline" href={urls.comparison_xlsx} target="_blank" rel="noreferrer">
              Comparison spreadsheet (.xlsx)
            </a>
          </li>
        )}
        {urls.dashboard_html && (
          <li>
            <a className="text-blue-600 hover:underline" href={urls.dashboard_html} target="_blank" rel="noreferrer">
              Panel dashboard (.html)
            </a>
          </li>
        )}
      </ul>
    </section>
  );
}
