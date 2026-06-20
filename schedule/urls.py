from django.urls import path

from .views import (
    ClassRegistrationCancelView,
    ClassRegistrationCreateView,
    ClassRegistrationMissedView,
    ClassRegistrationVisitedView,
    FitnessClassCancelView,
    FitnessClassCompleteView,
    FitnessClassCreateView,
    FitnessClassDetailView,
    FitnessClassListView,
    FitnessClassUpdateView,
    MyClassesView,
)

app_name = 'schedule'

urlpatterns = [
    path('', FitnessClassListView.as_view(), name='list'),
    path('create/', FitnessClassCreateView.as_view(), name='create'),
    path('my/', MyClassesView.as_view(), name='my'),

    path('<int:pk>/', FitnessClassDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', FitnessClassUpdateView.as_view(), name='edit'),
    path('<int:pk>/cancel/', FitnessClassCancelView.as_view(), name='cancel'),
    path('<int:pk>/complete/', FitnessClassCompleteView.as_view(), name='complete'),

    path('<int:class_id>/register/', ClassRegistrationCreateView.as_view(), name='register'),

    path('registrations/<int:pk>/cancel/', ClassRegistrationCancelView.as_view(), name='registration_cancel'),
    path('registrations/<int:pk>/visited/', ClassRegistrationVisitedView.as_view(), name='registration_visited'),
    path('registrations/<int:pk>/missed/', ClassRegistrationMissedView.as_view(), name='registration_missed'),
]