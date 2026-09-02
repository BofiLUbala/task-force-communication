import { useEffect, useMemo, useState } from 'react';
import PreferencesContext from './PreferencesContext';

export default function PreferencesProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  const [language, setLanguage] = useState(() => localStorage.getItem('language') || 'fr');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language;
    localStorage.setItem('language', language);
  }, [language]);

  const value = useMemo(() => ({
    theme,
    language,
    toggleTheme: () => setTheme((current) => current === 'dark' ? 'light' : 'dark'),
    setLanguage,
    tr: (fr, en) => language === 'fr' ? fr : en,
  }), [theme, language]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}
