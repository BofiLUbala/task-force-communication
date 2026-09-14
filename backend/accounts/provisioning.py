"""Rules governing which accounts may be created, and by whom.

The platform is staffed top-down and has a fixed number of staff seats:

* ``SUPER_ADMIN`` — technical owner of the application. One seat.
* ``HIERARCHY``   — operational leads, who staff the field. Two seats, so
  the field is never blocked when one of them is away.

Three staff accounts in total; everything beyond that is a field agent.
Public signup exists solely to fill those posts, in that order, and closes
for good once every seat is taken. Everyone else joins by invitation: the
super admin provisions the hierarchy seats, and the hierarchy invites the
field agents.

The cap is enforced at the ways accounts are actually provisioned — the
invitation endpoint, public signup and ``grant_role`` — rather than in
``User.save()``. Direct ORM writes (data migrations, ``createsuperuser``,
tests building a fixture) stay deliberately unblocked.
"""
from .models import User


def role_capacity(role):
    """Seats this post has in total, or ``None`` when it is unlimited."""
    return User.ROLE_CAPACITY.get(role)


def role_occupancy(role):
    """Accounts currently holding the post, invited-but-not-yet-active included.

    An outstanding invitation occupies its seat: two people must never be
    invited onto the same post and discover the clash at activation.
    """
    return User.objects.filter(role=role).count()


def remaining_seats(role):
    """Seats left on a post. ``None`` means unlimited."""
    capacity = role_capacity(role)
    if capacity is None:
        return None
    return max(capacity - role_occupancy(role), 0)


def role_post_is_vacant(role):
    """True when the post can still take one more account."""
    remaining = remaining_seats(role)
    return True if remaining is None else remaining > 0


def capacity_error(role):
    """Refusal message when a post is full, or ``None`` when it can take one.

    Phrased for whoever is trying to provision the account, so the answer
    carries the way out rather than only the refusal.
    """
    if role_post_is_vacant(role):
        return None

    label = User.Role(role).label
    capacity = role_capacity(role)
    occupied = role_occupancy(role)

    if capacity == 1:
        return (
            f'Un compte « {label} » existe déjà. '
            'Supprimez-le avant d’en inviter un autre.'
        )
    detail = (
        f'Le poste « {label} » est complet '
        f'({occupied}/{capacity} comptes, invitations en attente comprises). '
        'Supprimez ou révoquez un compte existant avant d’en inviter un autre.'
    )
    if occupied > capacity:
        # The seats were reduced after these accounts already existed; say so
        # instead of leaving an impossible-looking count unexplained.
        detail += (
            f' Ce poste compte actuellement {occupied} comptes, au-delà de la '
            f'limite de {capacity} : aucun nouveau compte ne sera accepté tant '
            'que ce nombre ne sera pas redescendu.'
        )
    return detail


def open_registration_role():
    """Role the public signup page would create right now, or ``None`` when closed."""
    for role in (User.Role.SUPER_ADMIN, User.Role.HIERARCHY):
        if role_post_is_vacant(role):
            return role
    return None
