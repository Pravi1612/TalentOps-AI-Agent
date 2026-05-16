import { useState } from 'react';
import ChecklistEditor from './ChecklistEditor.jsx';
import { ingest } from '../api/client.js';

export default function UploadPanel({ onStart, onError }) {
  const [files, setFiles] = useState([]);
  const [roleDescription, setRoleDescription] = useState('');
  const [checklist, setChecklist] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleFileChange = (e) => {
    const picked = Array.from(e.target.files || []).filter((f) =>
      f.name.toLowerCase().endsWith('.pdf'),
    );
    setFiles(picked);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    onError?.(null);

    if (files.length < 3 || files.length > 10) {
      onError?.('Please attach between 3 and 10 PDF resumes.');
      return;
    }
    if (!checklist || !checklist.role_title) {
      onError?.('Provide a valid evaluation checklist.');
      return;
    }

    setSubmitting(true);
    try {
      const data = await ingest({ resumes: files, checklist, roleDescription });
      onStart?.(data.session_id);
    } catch (err) {
      onError?.(err?.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded shadow-sm p-6 space-y-5 border border-slate-200">
      <h2 className="text-lg font-semibold">Upload candidate batch</h2>
      <p className="text-sm text-slate-600">
        Attach 3–10 candidate resumes (PDF), paste the role description, and edit the
        evaluation checklist below.
      </p>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Resumes (PDF, 3–10 files)
        </label>
        <input
          type="file"
          multiple
          accept="application/pdf"
          onChange={handleFileChange}
          className="block w-full text-sm border border-slate-300 rounded p-2"
        />
        {files.length > 0 && (
          <p className="text-xs text-slate-600 mt-1">
            {files.length} file(s) selected: {files.map((f) => f.name).join(', ')}
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Role description
        </label>
        <textarea
          value={roleDescription}
          onChange={(e) => setRoleDescription(e.target.value)}
          rows={6}
          className="w-full border border-slate-300 rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Paste the JD text here…"
        />
      </div>

      <ChecklistEditor value={checklist} onChange={setChecklist} />

      <button
        type="submit"
        disabled={submitting}
        className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white px-4 py-2 rounded font-medium"
      >
        {submitting ? 'Submitting…' : 'Run analysis'}
      </button>
    </form>
  );
}
