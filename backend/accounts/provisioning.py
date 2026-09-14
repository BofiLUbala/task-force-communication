"""Rules governing which accounts may be created, and by whom.

The platform is staffed top-down and has exactly two singleton posts:

* ``SUPER_ADMIN`` — technical owner of the application.
* ``HIERARCHY``   — operational lead, the only one who staffs the field.

Public signup exists solely to fill those two posts, in that order, and
closes for good once both are taken. Everyone else joins by invitation:
the super admin provisions the hierarchy post if it is vacant, and the
hierarchy invites the field agents.
"""
from .models import User


def open_registration_role():
    """Role the public signup page would create right now, or ``None`` when closed."""
    if not User.objects.filter(role=User.Role.SUPER_ADMIN).exists():
        return User.Role.SUPER_ADMIN
    if not User.objects.filter(role=User.Role.HIERARCHY).exists():
        return User.Role.HIERARCHY
    return None


def role_post_is_vacant(role):
    """True when a singleton post currently has no account at all."""
    return role in User.SINGLETON_ROLES and not User.objects.filter(role=role).exists()
