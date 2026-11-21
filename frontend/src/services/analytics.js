import { api } from './api';
export const getSummary = params => api.get('/analytics/summary', { params }).then(r => r.data);
export const getOverdue = params => api.get('/analytics/overdue', { params }).then(r => r.data);
export const getMonthly = () => api.get('/analytics/monthly').then(r => r.data);
