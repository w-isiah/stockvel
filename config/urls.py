

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('pages', include('apps.pages.urls')),
    path('contributions/', include('apps.contributions.urls')),
    path('investments/', include('apps.investments.urls')),
    path('withdrawals/', include('apps.withdrawals.urls')),
    path('loans/', include('apps.loans.urls')),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


