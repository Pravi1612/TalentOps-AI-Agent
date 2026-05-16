const PILL_COLOR = {
  Meets: 'bg-green-100 text-green-800',
  'Partially Meets': 'bg-amber-100 text-amber-800',
  'Does Not Meet': 'bg-red-100 text-red-800',
  Present: 'bg-green-100 text-green-800',
  Absent: 'bg-slate-100 text-slate-600',
  None: 'bg-green-100 text-green-800',
  Minor: 'bg-amber-100 text-amber-800',
  Major: 'bg-red-100 text-red-800',
};

function Pill({ rating }) {
  if (!rating) return <span className="text-slate-400">—</span>;
  const cls = PILL_COLOR[rating] || 'bg-slate-100 text-slate-700';
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {rating}
    </span>
  );
}

export default function ComparisonTable({ comparison, briefing }) {
  if (!comparison) return null;
  const skills = new Set();
  comparison.rows.forEach((row) =>
    Object.keys(row.must_have_ratings || {}).forEach((s) => skills.add(s)),
  );
  const skillList = Array.from(skills);

  return (
    <section className="bg-white rounded shadow-sm border border-slate-200 p-4">
      <header className="mb-3">
        <h2 className="text-lg font-semibold">Side-by-side comparison</h2>
        <p className="text-xs text-slate-500">Role: {comparison.role_title}</p>
      </header>

      {briefing && (
        <div className="bg-slate-50 border border-slate-200 rounded p-3 mb-4 text-sm">
          <p className="font-medium mb-1">{briefing.headline}</p>
          {briefing.panel_focus_areas?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500 mt-2">
                Panel focus areas
              </p>
              <ul className="list-disc pl-5 text-sm">
                {briefing.panel_focus_areas.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-slate-900 text-white">
              <th className="text-left p-2">Candidate</th>
              {skillList.map((s) => (
                <th key={s} className="text-left p-2">{s}</th>
              ))}
              <th className="text-left p-2">Red flag</th>
              <th className="text-left p-2">Focus</th>
            </tr>
          </thead>
          <tbody>
            {comparison.rows.map((row, i) => (
              <tr key={i} className="border-b border-slate-100">
                <td className="p-2 font-medium">{row.candidate_name}</td>
                {skillList.map((s) => (
                  <td key={s} className="p-2">
                    <Pill rating={row.must_have_ratings?.[s]} />
                  </td>
                ))}
                <td className="p-2">
                  <Pill rating={row.red_flag_status} />
                </td>
                <td className="p-2 text-xs text-slate-600">
                  {row.recommended_focus_areas?.length ? (
                    <ul className="list-disc pl-4">
                      {row.recommended_focus_areas.map((f, j) => (
                        <li key={j}>{f}</li>
                      ))}
                    </ul>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
