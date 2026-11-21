import { api } from './api';
export const listInvoices = params => api.get('/invoices', { params }).then(r => r.data);
export const getInvoice = id => api.get(`/invoices/${id}`).then(r => r.data);
export const extractInvoice = file => { const form = new FormData(); form.append('file', file); return api.post('/invoices/extract', form).then(r => r.data); };
export const saveInvoice = data => api.post('/invoices', data).then(r => r.data);
export const updateInvoice = (id, data) => api.patch(`/invoices/${id}`, data).then(r => r.data);
export const deleteInvoice = id => api.delete(`/invoices/${id}`).then(r => r.data);
