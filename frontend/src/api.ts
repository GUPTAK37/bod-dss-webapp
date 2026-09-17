import axios from 'axios';

/**
 * Resolve the API base URL at runtime.
 *
 * The SPA is served from `<mount>/app/` — under DSS that's something like
 * `https://dss.example.com/public/webapps/<PROJ>/backend/<hash>/app/`. The
 * matching API lives at the sibling `<mount>/api/` path.
 *
 * Under Vite dev the SPA is at `http://localhost:5173/`, no `/app` prefix,
 * so we fall back to `/api` — the Vite proxy forwards that to :8000.
 */
function computeApiBase(): string {
  const path = window.location.pathname;
  const m = path.match(/^(.*?)\/app(?:\/.*)?$/);
  if (m) return `${m[1]}/api`;
  return '/api';
}

const API_BASE = computeApiBase();

const api = axios.create({ baseURL: API_BASE });

export const getRefreshDate    = () => api.get('/refresh-date').then((r) => r.data);
export const getFilterOptions  = () => api.get('/filter-options').then((r) => r.data);
export const getMe             = () => api.get('/me').then((r) => r.data);
export const postFilterCascade = (body: any) =>
  api.post('/filter-cascade', body).then((r) => r.data);
export const postHrTop7        = (filters: any) =>
  api.post('/hr-top7', filters).then((r) => r.data);
export const fetchSection      = (sid: string, filters: any) =>
  api.post(`/section/${sid}`, filters).then((r) => r.data);

export default api;
