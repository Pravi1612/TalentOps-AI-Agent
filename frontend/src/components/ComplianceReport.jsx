export default function ComplianceReport({ report }) {
  if (!report) return null;
  return (
    <section className="bg-white rounded shadow-sm border border-slate-200 p-4">
      <header className="mb-3">
        <h2 className="text-lg font-semibold">Compliance gap report</h2>
        <p className="text-xs text-slate-500">
          Required checks: {report.all_required_checks?.join(', ') || 'none defined'}
        </p>
      </header>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-slate-900 text-white">
              <th className="text-left p-2">Candidate</th>
              <th className="text-left p-2">Missing required checks</th>
            </tr>
          </thead>
          <tbody>
            {report.gaps?.map((gap, i) => (
              <tr key={i} className="border-b border-slate-100">
                <td className="p-2 font-medium">{gap.candidate_name}</td>
                <td className="p-2 text-slate-700">
                  {gap.missing_checks?.length
                    ? gap.missing_checks.join(', ')
                    : <span className="text-green-700">None</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
