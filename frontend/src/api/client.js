import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
});

export async function ingest({ resumes, checklist, roleDescription }) {
  const form = new FormData();
  resumes.forEach((file) => form.append('resumes', file));
  form.append('checklist', JSON.stringify(checklist));
  if (roleDescription) form.append('role_description', roleDescription);
  const { data } = await api.post('/ingest', form);
  return data;
}

export async function getStatus(sessionId) {
  const { data } = await api.get(`/session/${sessionId}/status`);
  return data;
}

export async function getResults(sessionId) {
  const { data } = await api.get(`/session/${sessionId}/results`);
  return data;
}

export function downloadUrl(path) {
  if (!path) return null;
  return path.startsWith('/api') ? path : `/api/v1/download/${path}`;
}

export async function getHealth() {
  const { data } = await api.get('/health');
  return data;
}
