import { useEffect, useState } from 'react';

const KEY = 'bizflow-theme';

function initialTheme() {
  try { return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light'; } catch { return 'light'; }
}

export function useTheme() {
  const [theme, setTheme] = useState(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem(KEY, theme); } catch { /* storage blocked */ }
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0d1417' : '#f8fafc');
  }, [theme]);
  return [theme, () => setTheme(t => (t === 'dark' ? 'light' : 'dark'))];
}
