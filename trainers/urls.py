from django.urls import path

from .views import (
    TrainerClientAddView,
    TrainerClientRemoveView,
    TrainerClientsView,
    TrainerCreateView,
    TrainerDeleteView,
    TrainerDetailView,
    TrainerListView,
    TrainerMyClassesView,
    TrainerUpdateView,
)

app_name = 'trainers'

urlpatterns = [
    path('', TrainerListView.as_view(), name='list'),
    path('create/', TrainerCreateView.as_view(), name='create'),

    path('my/classes/', TrainerMyClassesView.as_view(), name='my_classes'),
    path('my/clients/', TrainerClientsView.as_view(), name='my_clients'),
    path('my/clients/add/', TrainerClientAddView.as_view(), name='my_clients_add'),
    path(
        'my/clients/<int:assignment_pk>/remove/',
        TrainerClientRemoveView.as_view(),
        name='my_clients_remove',
    ),

    path('<int:pk>/', TrainerDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', TrainerUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', TrainerDeleteView.as_view(), name='delete'),

    path('<int:pk>/clients/', TrainerClientsView.as_view(), name='clients'),
    path('<int:pk>/clients/add/', TrainerClientAddView.as_view(), name='clients_add'),
    path(
        '<int:pk>/clients/<int:assignment_pk>/remove/',
        TrainerClientRemoveView.as_view(),
        name='clients_remove',
    ),
]