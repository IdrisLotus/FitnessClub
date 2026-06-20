from django.urls import path

from .views import VisitCancelView, VisitListView

app_name = 'visits'

urlpatterns = [
    path('', VisitListView.as_view(), name='list'),
    path('<int:pk>/cancel/', VisitCancelView.as_view(), name='cancel'),
]