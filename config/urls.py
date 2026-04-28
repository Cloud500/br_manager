"""
Root URL configuration for the BR Manager project.

Routes all app-specific URL patterns to their respective
app modules and includes admin, debug toolbar (in DEBUG mode),
and media file serving.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("roles/", include("apps.roles.urls", namespace="roles")),
    path("committees/", include("apps.committees.urls", namespace="committees")),
    path("meetings/", include("apps.meetings.urls", namespace="meetings")),
    path("agendas/", include("apps.agendas.urls", namespace="agendas")),
    path("", include("apps.core.urls", namespace="core")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls))
        ] + urlpatterns
    except ImportError:
        pass
