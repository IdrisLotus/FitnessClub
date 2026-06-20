from django.urls import path

from .views import PaymentCancelView, PaymentCreateView, PaymentListView

app_name = 'payments'

urlpatterns = [
    path('', PaymentListView.as_view(), name='list'),
    path('clients/<int:client_id>/payments/create/', PaymentCreateView.as_view(), name='create'),
    path('<int:pk>/cancel/', PaymentCancelView.as_view(), name='cancel'),
]