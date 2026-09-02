from rest_framework.routers import DefaultRouter

from .views import PublicPostViewSet, ReportViewSet

router = DefaultRouter()
router.register('reports', ReportViewSet, basename='report')
router.register('posts', PublicPostViewSet, basename='post')

urlpatterns = router.urls
