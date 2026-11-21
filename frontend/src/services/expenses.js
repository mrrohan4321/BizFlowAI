import { api } from './api';
export const listExpenses = params => api.get('/expenses', { params }).then(r => r.data);
export const addExpense = data => api.post('/expenses', data).then(r => r.data);
export const markExpensePaid = (id, paid_date) => api.patch(`/expenses/${id}`, { payment_status: 'paid', paid_date }).then(r => r.data);
