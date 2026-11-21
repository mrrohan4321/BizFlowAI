import { api } from './api';
export const askAssistant = question => api.post('/assistant/chat', { question }).then(r => r.data);
