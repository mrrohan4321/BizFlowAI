import axios from 'axios';
import { supabase, signOut } from './supabase';

const messages = {
  unauthenticated: 'Your session has expired. Please sign in again.', no_business_access: 'No business is linked to this account. Please contact support to link your account to a business.', forbidden_business: 'You do not have access to that business.', business_required: 'Your account has multiple businesses. Select one with a business ID.', invalid_business_id: 'That business ID is invalid.', duplicate_invoice: 'An invoice with this number and type already exists. Change its number or open the existing invoice.', extraction_already_used: 'This extraction has already been saved.', extraction_expired: 'Your review session expired. Please upload the invoice again.', invoice_has_payments: 'This invoice has payments and cannot be deleted.', opening_cash_required: 'Set an opening cash balance to generate a forecast.', file_too_large: 'Files must be no larger than 10 MB.', unsupported_file_type: 'Please upload a PDF, JPG or PNG.', overpayment: 'The amount exceeds the outstanding balance.', assistant_failed: 'The assistant is temporarily unavailable. Please try again.', ai_not_configured: 'AI is not configured on the server.', ocr_unavailable: 'Document reading is temporarily unavailable.', database_error: 'The server could not access the database. Please try again.'
};
export function apiError(error) {
  const payload = error?.response?.data?.error;
  const code = payload?.code || (error?.response?.status === 401 ? 'unauthenticated' : 'network_error');
  const message = messages[code] || payload?.message || (error?.response ? 'Something went wrong. Please try again.' : 'Unable to reach the server. It may be waking up (up to a minute). Please retry.');
  return Object.assign(new Error(message), { code, details: payload?.details || [], status: error?.response?.status });
}
export const api = axios.create({ baseURL: `${(import.meta.env.VITE_API_URL || '').replace(/\/$/, '')}/api`, timeout: 110000 });
api.interceptors.request.use(async (config) => {
  if (!supabase) throw new Error('Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to .env.');
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) { window.dispatchEvent(new Event('bizflow:unauthorized')); throw new Error('Please sign in again.'); }
  config.headers.Authorization = `Bearer ${data.session.access_token}`;
  const business = sessionStorage.getItem('bizflow_business_id');
  if (business) config.headers['X-Business-Id'] = business;
  return config;
});
api.interceptors.response.use(r => r, async (error) => {
  const friendly = apiError(error);
  if (friendly.status === 401) { await signOut(); window.dispatchEvent(new Event('bizflow:unauthorized')); }
  return Promise.reject(friendly);
});
export const setBusinessId = id => { if (id) sessionStorage.setItem('bizflow_business_id', id); else sessionStorage.removeItem('bizflow_business_id'); };
