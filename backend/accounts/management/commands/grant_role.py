"""Assign a platform role from the command line.

Escape hatch for bootstrapping and recovery: the super admin and hierarchy
posts can each be filled only once through the web signup, so an operator
needs a way to (re)designate them without touching the database by hand.
"""
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = 'Grant a platform role (SUPER_ADMIN, HIERARCHY, AGENT) to an existing account.'

    def add_arguments(self, parser):
        parser.add_argument('email', help='E-mail address of the account.')
        parser.add_argument('role', choices=[role.value for role in User.Role])
        parser.add_argument(
            '--force', action='store_true',
            help='Take over a singleton post that is already held by someone else.',
        )

    def handle(self, *args, **options):
        email, role, force = options['email'], options['role'], options['force']

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise CommandError(f'Aucun compte avec l’adresse {email}.')

        if role in User.SINGLETON_ROLES:
            holder = User.objects.filter(role=role).exclude(pk=user.pk).first()
            if holder and not force:
                raise CommandError(
                    f'Le poste « {User.Role(role).label} » est déjà occupé par {holder.email}. '
                    'Relancez avec --force pour le transférer.'
                )
            if holder:
                holder.role = User.Role.AGENT
                holder.save(update_fields=('role',))
                self.stdout.write(self.style.WARNING(f'{holder.email} rétrogradé en agent.'))
        elif role in User.STAFF_ROLES and user.role != role:
            # A post with several seats has no single holder to hand over to,
            # so there is nothing --force could unambiguously replace: the
            # operator has to say which seat they are freeing.
            capacity = User.ROLE_CAPACITY[role]
            occupied = User.objects.filter(role=role).exclude(pk=user.pk).count()
            if occupied >= capacity:
                raise CommandError(
                    f'Le poste « {User.Role(role).label} » est complet '
                    f'({occupied}/{capacity}). Libérez une place avant d’en attribuer une autre.'
                )

        user.role = role
        user.save(update_fields=('role',))
        if not user.is_active:
            user.mark_active()
            self.stdout.write(self.style.WARNING(f'{user.email} activé.'))

        self.stdout.write(self.style.SUCCESS(f'{user.email} a désormais le rôle {User.Role(role).label}.'))
