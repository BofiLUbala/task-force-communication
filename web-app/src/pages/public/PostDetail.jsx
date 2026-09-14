import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import usePreferences from '../../hooks/usePreferences';
import './Listing.css';
import './PostDetail.css';

const CATEGORY_EDIT_PATH = {
  COMMUNIQUE: '/espace/publications/communique',
  ACTUALITE: '/espace/publications/actualite',
  NEWSLETTER: '/espace/publications/newsletter',
};

function editPathFor(post) {
  if (post.category !== 'ACTIVITE') return CATEGORY_EDIT_PATH[post.category] || '/espace/publications/actualite';
  const hasVideo = (post.gallery || []).some((m) => m.media_type === 'VIDEO');
  return hasVideo ? '/espace/publications/video' : '/espace/publications/image';
}

const CATEGORY_BACK_PATH = {
  COMMUNIQUE: '/actualites',
  ACTUALITE: '/actualites',
  ACTIVITE: '/activites',
  NEWSLETTER: '/newsletter',
};

function categoryLabel(category, tr) {
  return {
    COMMUNIQUE: tr('Communiqué', 'Release'),
    ACTUALITE: tr('Actualité', 'News'),
    ACTIVITE: tr('Activité', 'Activity'),
    NEWSLETTER: tr('Newsletter', 'Newsletter'),
  }[category] || category;
}

export default function PostDetail() {
  const { slug } = useParams();
  const { tr, language } = usePreferences();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setLoading(true);
    setNotFound(false);
    client.get(`/posts/${slug}/`)
      .then((res) => setPost(res.data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [slug]);

  async function handleDelete() {
    // eslint-disable-next-line no-alert
    if (!window.confirm(tr('Supprimer définitivement cette publication ?', 'Permanently delete this publication?'))) return;
    setDeleting(true);
    try {
      await client.delete(`/posts/${slug}/`);
      navigate(CATEGORY_BACK_PATH[post.category] || '/actualites');
    } catch {
      setDeleting(false);
      // eslint-disable-next-line no-alert
      window.alert(tr('La suppression a échoué.', 'Deletion failed.'));
    }
  }

  const canManage = post && user && (user.id === post.published_by || user.role === 'HIERARCHY');

  if (loading) {
    return <div className="post-detail-page"><p className="post-detail-loading">{tr('Chargement...', 'Loading...')}</p></div>;
  }

  if (notFound || !post) {
    return (
      <div className="post-detail-page">
        <p>{tr('Cette publication est introuvable.', 'This publication could not be found.')}</p>
        <Link to="/actualites" className="page-back-link" style={{ color: 'var(--primary)' }}>
          <span className="material-symbols-outlined">arrow_back</span>
          {tr('Retour aux actualités', 'Back to news')}
        </Link>
      </div>
    );
  }

  // Documents are listed for download; only visual media belong in the gallery,
  // otherwise a PDF would render as an empty <video> element.
  const visualMedia = (post.gallery || []).filter((m) => m.media_type !== 'DOCUMENT');
  const documents = (post.gallery || []).filter((m) => m.media_type === 'DOCUMENT');

  return (
    <div className="post-detail-page">
      <div className="post-detail-header">
        <Link to={CATEGORY_BACK_PATH[post.category] || '/actualites'} className="page-back-link" style={{ color: 'var(--primary)' }}>
          <span className="material-symbols-outlined">arrow_back</span>
          {tr('Retour', 'Back')}
        </Link>

        {canManage && (
          <div className="post-detail-actions">
            <Link to={`${editPathFor(post)}/${post.slug}`} className="btn-icon">
              <span className="material-symbols-outlined">edit</span>
              {tr('Modifier', 'Edit')}
            </Link>
            <button type="button" className="btn-icon btn-icon-danger" onClick={handleDelete} disabled={deleting}>
              <span className="material-symbols-outlined">delete</span>
              {deleting ? tr('Suppression...', 'Deleting...') : tr('Supprimer', 'Delete')}
            </button>
          </div>
        )}
      </div>

      <span className="chip">{categoryLabel(post.category, tr)}</span>
      <h1 className="post-detail-title">{post.title}</h1>
      <div className="post-detail-meta">
        <span className="material-symbols-outlined">calendar_today</span>
        {new Date(post.published_at || post.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US', {
          day: 'numeric', month: 'long', year: 'numeric',
        })}
        {post.published_by_name && <span> · {post.published_by_name}</span>}
      </div>

      {post.cover_image && (
        <img src={post.cover_image} alt={post.title} className="post-detail-cover" />
      )}

      <div className="post-detail-body" dangerouslySetInnerHTML={{ __html: post.body }} />

      {post.attachment && (
        <a href={post.attachment} target="_blank" rel="noopener noreferrer" className="post-detail-attachment">
          <span className="material-symbols-outlined">picture_as_pdf</span>
          {tr('Télécharger le document', 'Download the document')}
        </a>
      )}

      {visualMedia.length > 0 && (
        <div className="post-detail-gallery">
          {visualMedia.map((item) => {
            if (item.media_type === 'PHOTO') {
              return <img key={item.id} src={item.file} alt={item.alt_text || item.caption || post.title} />;
            }
            if (item.media_type === 'AUDIO') {
              return <audio key={item.id} controls preload="metadata" src={item.file} />;
            }
            return (
              <video key={item.id} controls preload="metadata" playsInline poster={item.thumbnail || undefined}>
                <source src={item.file} />
              </video>
            );
          })}
        </div>
      )}

      {documents.length > 0 && (
        <div className="post-detail-documents">
          <h2>{tr('Documents', 'Documents')}</h2>
          {documents.map((item) => (
            <a
              key={item.id}
              href={item.file}
              target="_blank"
              rel="noopener noreferrer"
              className="post-detail-attachment"
            >
              <span className="material-symbols-outlined">description</span>
              {item.title || item.original_filename || tr('Télécharger le document', 'Download the document')}
            </a>
          ))}
        </div>
      )}

      {post.links && post.links.length > 0 && (
        <div className="post-detail-links">
          <h2>{tr('Liens', 'Links')}</h2>
          <ul>
            {post.links.map((link) => (
              <li key={link.id}>
                <a href={link.url} target="_blank" rel="noopener noreferrer">
                  <span className="material-symbols-outlined">open_in_new</span>
                  {link.label || link.url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
