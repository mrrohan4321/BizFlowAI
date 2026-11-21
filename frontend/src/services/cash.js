import { api } from './api';
export const getOpeningCash = () => api.get('/opening-cash').then(r => r.data);
export const saveOpeningCash = data => api.put('/opening-cash', data).then(r => r.data);
export const getForecast = params => api.get('/forecast', { params }).then(r => r.data);
