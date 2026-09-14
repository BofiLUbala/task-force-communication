/**
 * The internal sidebar, in one place.
 *
 * There used to be five "Publier un(e) ..." entries — one per content type —
 * duplicated across four dashboard files. Publication type is metadata now, so
 * there is a single Publications section and a single `+ Nouvelle publication`
 * button instead.
 */
export function internalLinks(role, tr) {
  const publications = [
    { to: '/espace/publications', label: tr('Publications', 'Publications') },
    { to: '/espace/publications/nouvelle', label: tr('Nouvelle publication', 'New publication') },
    { to: '/espace/publications/brouillons', label: tr('Brouillons', 'Drafts') },
    { to: '/espace/publications/programmees', label: tr('Programmées', 'Scheduled') },
    { to: '/espace/reseaux-sociaux', label: tr('Diffusion & réseaux', 'Distribution & networks') },
  ];

  if (role === 'HIERARCHY') {
    return [
      { to: '/espace/validation', label: tr('Rapports en attente', 'Pending reports') },
      { to: '/espace/agents', label: tr('Comptes agents', 'Agent accounts') },
      ...publications,
    ];
  }
  return [
    { to: '/espace/rapports', label: tr('Mes rapports', 'My reports') },
    ...publications,
  ];
}
