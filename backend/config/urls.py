from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve


def health(_request):
    """Liveness + database readiness, for the platform's health check.

    A process that has booted but cannot reach Postgres is not healthy, so the
    check touches the connection rather than only returning 200.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        database = 'ok'
    except Exception:  # noqa: BLE001 — the health endpoint must never raise
        database = 'unavailable'
    return JsonResponse(
        {'status': 'ok' if database == 'ok' else 'degraded', 'database': database},
        status=200 if database == 'ok' else 503,
    )


urlpatterns = [
    path('healthz/', health, name='health'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('content.urls')),
]

# Uploads. With object storage configured the files are served by the bucket
# and Django never sees these URLs. Without it, Django serves MEDIA_ROOT
# itself — correct only when that path is a persistent volume, and the reason
# `USE_OBJECT_STORAGE` exists for platforms with an ephemeral filesystem.
if settings.DEBUG or not settings.USE_OBJECT_STORAGE:
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
