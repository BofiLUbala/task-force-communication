import usePreferences from '../hooks/usePreferences';
import './PreferenceControls.css';

export default function PreferenceControls({ compact = false }) {
  const { theme, language, toggleTheme, setLanguage, tr } = usePreferences();

  return (
    <div className={`preference-controls ${compact ? 'compact' : ''}`}>
      <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label={tr('Changer le thème', 'Change theme')} title={tr('Mode clair ou sombre', 'Light or dark mode')}>
        <span className="material-symbols-outlined">{theme === 'dark' ? 'light_mode' : 'dark_mode'}</span>
        {!compact && <span>{theme === 'dark' ? tr('Clair', 'Light') : tr('Sombre', 'Dark')}</span>}
      </button>
      <label className="language-control">
        <span className="material-symbols-outlined">language</span>
        <span className="sr-only">{tr('Langue', 'Language')}</span>
        <select value={language} onChange={(event) => setLanguage(event.target.value)} aria-label={tr('Langue', 'Language')}>
          <option value="fr">FR</option>
          <option value="en">EN</option>
        </select>
      </label>
    </div>
  );
}
