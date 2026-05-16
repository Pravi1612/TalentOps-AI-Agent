import { useState } from 'react';

const CATEGORY_COLOR = {
  'Technical Depth': 'bg-blue-100 text-blue-800',
  'Behavioural Scenarios': 'bg-purple-100 text-purple-800',
  'Gap Probing': 'bg-amber-100 text-amber-800',
  Situational: 'bg-emerald-100 text-emerald-800',
};

export default function QuestionBankView({ candidates }) {
  const [openIdx, setOpenIdx] = useState(0);
  if (!candidates?.length) return null;

  return (
    <section className="bg-white rounded shadow-sm border border-slate-200 p-4">
      <h2 className="text-lg font-semibold mb-3">Interview question banks</h2>
      <div className="flex flex-wrap gap-2 mb-4">
        {candidates.map((c, i) => (
          <button
            key={i}
            onClick={() => setOpenIdx(i)}
            className={`px-3 py-1 text-sm rounded ${
              openIdx === i
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {c.profile.full_name}
          </button>
        ))}
      </div>

      <Bank bundle={candidates[openIdx]} />
    </section>
  );
}

function Bank({ bundle }) {
  const bank = bundle?.questions;
  if (!bank?.questions?.length) return <p className="text-sm text-slate-500">No questions.</p>;

  const grouped = bank.questions.reduce((acc, q) => {
    acc[q.category] = acc[q.category] || [];
    acc[q.category].push(q);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([category, qs]) => (
        <div key={category}>
          <h3 className="text-sm font-semibold mb-2">
            <span className={`inline-block rounded px-2 py-0.5 mr-2 ${CATEGORY_COLOR[category] || 'bg-slate-100'}`}>
              {category}
            </span>
            <span className="text-slate-500">({qs.length})</span>
          </h3>
          <ol className="list-decimal pl-5 text-sm space-y-2">
            {qs.map((q, i) => (
              <li key={i}>
                <p className="font-medium">{q.question}</p>
                <p className="text-xs text-slate-500 italic">Why: {q.rationale}</p>
                {q.expected_signals?.length > 0 && (
                  <p className="text-xs text-slate-500">
                    Listen for: {q.expected_signals.join(', ')}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}
