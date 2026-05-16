import { useEffect, useState } from 'react';

const DEFAULT_CHECKLIST = {
  role_title: 'Senior Backend Engineer',
  must_have_skills: [
    { name: 'Python', description: '5+ years production experience' },
    { name: 'Distributed systems', description: 'Designed services at scale' },
  ],
  nice_to_have_skills: [{ name: 'Kubernetes' }, { name: 'Go' }],
  red_flag_indicators: [
    'Job-hopping with <12 month tenures',
    'Unexplained gap > 12 months',
    'Title/responsibility mismatch',
  ],
  min_years_experience: 5,
  compliance_checks: [
    { name: 'Background verification', required: true, description: 'BGV consent and clearance' },
    { name: 'Right to work', required: true, description: 'Work authorisation confirmed' },
    { name: 'Video consent', required: true, description: 'Recording consent form signed' },
  ],
};

export default function ChecklistEditor({ value, onChange }) {
  const [raw, setRaw] = useState(JSON.stringify(value || DEFAULT_CHECKLIST, null, 2));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!value) {
      onChange?.(DEFAULT_CHECKLIST);
    }
  }, []);

  const handleChange = (e) => {
    const next = e.target.value;
    setRaw(next);
    try {
      const parsed = JSON.parse(next);
      setError(null);
      onChange?.(parsed);
    } catch (err) {
      setError(err.message);
    }
  };

  const reset = () => {
    const text = JSON.stringify(DEFAULT_CHECKLIST, null, 2);
    setRaw(text);
    setError(null);
    onChange?.(DEFAULT_CHECKLIST);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-slate-700">
          Evaluation checklist (JSON)
        </label>
        <button
          type="button"
          onClick={reset}
          className="text-xs text-blue-600 hover:underline"
        >
          Reset to default
        </button>
      </div>
      <textarea
        value={raw}
        onChange={handleChange}
        rows={18}
        spellCheck={false}
        className="w-full font-mono text-xs border border-slate-300 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {error && (
        <p className="text-xs text-red-600">Invalid JSON: {error}</p>
      )}
    </div>
  );
}
