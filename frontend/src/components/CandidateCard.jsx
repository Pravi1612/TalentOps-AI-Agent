const RATING_CLASS = {
  Meets: 'bg-green-100 text-green-800',
  'Partially Meets': 'bg-amber-100 text-amber-800',
  'Does Not Meet': 'bg-red-100 text-red-800',
  Present: 'bg-green-100 text-green-800',
  Absent: 'bg-slate-100 text-slate-600',
  None: 'bg-green-100 text-green-800',
  Minor: 'bg-amber-100 text-amber-800',
  Major: 'bg-red-100 text-red-800',
};

function Tag({ label, rating }) {
  const cls = RATING_CLASS[rating] || 'bg-slate-100 text-slate-700';
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs mr-1 mb-1 ${cls}`}>
      {label}: {rating}
    </span>
  );
}

export default function CandidateCard({ bundle }) {
  const { profile, fitment, feedback_download_url, source_filename } = bundle;

  return (
    <article className="bg-white rounded shadow-sm border border-slate-200 p-4">
      <header className="mb-2">
        <h3 className="text-base font-semibold">{profile.full_name}</h3>
        <p className="text-xs text-slate-500">
          {profile.total_years_experience} yrs experience • {profile.career_progression}
          {profile.email ? ` • ${profile.email}` : ''}
        </p>
        <p className="text-xs text-slate-400">Source: {source_filename}</p>
      </header>

      <div className="mb-2">
        <p className="text-xs font-semibold uppercase text-slate-500">Must-haves</p>
        <div>
          {fitment.must_haves?.map((m, i) => (
            <Tag key={i} label={m.skill} rating={m.rating} />
          ))}
        </div>
      </div>

      {fitment.nice_to_haves?.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-semibold uppercase text-slate-500">Nice-to-haves</p>
          <div>
            {fitment.nice_to_haves.map((n, i) => (
              <Tag key={i} label={n.skill} rating={n.rating} />
            ))}
          </div>
        </div>
      )}

      {fitment.red_flags?.length > 0 && (
        <div className="mb-2">
          <p className="text-xs font-semibold uppercase text-slate-500">Red flags</p>
          <div>
            {fitment.red_flags.map((r, i) => (
              <Tag key={i} label={r.indicator} rating={r.rating} />
            ))}
          </div>
        </div>
      )}

      {fitment.overall_summary && (
        <p className="text-sm text-slate-700 italic mt-2">
          {fitment.overall_summary}
        </p>
      )}

      {feedback_download_url && (
        <a
          className="inline-block mt-3 text-sm text-blue-600 hover:underline"
          href={feedback_download_url}
          target="_blank"
          rel="noreferrer"
        >
          Download panelist feedback template (.docx)
        </a>
      )}
    </article>
  );
}
