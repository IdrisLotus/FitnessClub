from django.urls import path

from memberships.views import ClientMembershipCreateView
from payments.views import PaymentCreateView
from visits.views import VisitCreateView

from .views import (
    ClientCreateView,
    ClientDeleteView,
    ClientDetailView,
    ClientListView,
    ClientUpdateView,
)

app_name = 'clients'

urlpatterns = [
    path('', ClientListView.as_view(), name='list'),
    path('create/', ClientCreateView.as_view(), name='create'),
    path('<int:pk>/', ClientDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', ClientUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', ClientDeleteView.as_view(), name='delete'),

    path(
        '<int:client_id>/visit/',
        VisitCreateView.as_view(),
        name='visit_create',
    ),
    path(
        '<int:client_id>/memberships/create/',
        ClientMembershipCreateView.as_view(),
        name='membership_create',
    ),
    path(
        '<int:client_id>/payments/create/',
        PaymentCreateView.as_view(),
        name='payment_create',
    ),
]