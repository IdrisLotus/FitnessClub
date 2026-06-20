from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),

    path('admin/', admin.site.urls),

    path('accounts/', include('accounts.urls')),
    path('clients/', include('clients.urls')),
    path('trainers/', include('trainers.urls')),
    path('', include('memberships.urls')),

    path('visits/', include('visits.urls')),
    path('payments/', include('payments.urls')),
    path('classes/', include('schedule.urls')),

    path('', include('reports.urls')),
]