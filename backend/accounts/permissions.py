from rest_framework import permissions


class CanManageAccounts(permissions.BasePermission):
    """Only staff holding a managing post (super admin, hierarchy) may reach
    the account-management endpoints, and only for the roles they own."""

    message = "Vous n’êtes pas autorisé à gérer les comptes."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.manageable_roles)

    def has_object_permission(self, request, view, obj):
        return request.user.can_manage(obj)
