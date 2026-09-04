import usePreferences from '../hooks/usePreferences';
import './Pagination.css';

export default function Pagination({ page, pageSize, count, onChange }) {
  const { tr } = usePreferences();
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (totalPages <= 1) return null;

  const pages = [];
  for (let p = 1; p <= totalPages; p += 1) {
    if (p === 1 || p === totalPages || Math.abs(p - page) <= 1) {
      pages.push(p);
    } else if (pages[pages.length - 1] !== '…') {
      pages.push('…');
    }
  }

  return (
    <nav className="pagination" aria-label={tr('Pagination', 'Pagination')}>
      <button
        type="button"
        className="pagination-btn"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        <span className="material-symbols-outlined">chevron_left</span>
        {tr('Précédent', 'Previous')}
      </button>

      <div className="pagination-pages">
        {pages.map((p, i) => (p === '…' ? (
          <span key={`ellipsis-${i}`} className="pagination-ellipsis">…</span>
        ) : (
          <button
            key={p}
            type="button"
            className={`pagination-page ${p === page ? 'active' : ''}`}
            onClick={() => onChange(p)}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        )))}
      </div>

      <button
        type="button"
        className="pagination-btn"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
      >
        {tr('Suivant', 'Next')}
        <span className="material-symbols-outlined">chevron_right</span>
      </button>
    </nav>
  );
}
