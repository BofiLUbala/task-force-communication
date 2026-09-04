from rest_framework import permissions


class IsHierarchy(permissions.BasePermission):
    message = "Seule la hiérarchie peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_hierarchy)


class IsOwnerAgent(permissions.BasePermission):
    """Agents can only read/edit their own pending reports."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_hierarchy:
            return True
        return obj.submitted_by_id == request.user.id


class IsOwnerOrHierarchy(permissions.BasePermission):
    """Whoever published a post (agent or hierarchy) can edit/delete it;
    hierarchy can additionally edit/delete anyone's."""
    message = "Vous ne pouvez modifier que vos propres publications."

    def has_object_permission(self, request, view, obj):
        if request.user.is_hierarchy:
            return True
        return obj.published_by_id == request.user.id
