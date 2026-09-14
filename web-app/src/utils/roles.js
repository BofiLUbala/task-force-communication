export function roleLabel(role, tr) {
  if (role === 'SUPER_ADMIN') return tr('Super administrateur', 'Super administrator');
  if (role === 'HIERARCHY') return tr('Hiérarchie', 'Hierarchy');
  return tr('Agent terrain', 'Field agent');
}
