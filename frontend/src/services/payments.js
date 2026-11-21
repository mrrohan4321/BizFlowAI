import { api } from './api';
export const listPayments = params => api.get('/payments', { params }).then(r => r.data);
export const createPayment = data => api.post('/payments', data).then(r => r.data);
