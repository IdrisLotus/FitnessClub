from django.urls import path

from .views import (
    ClientsReportView,
    DashboardView,
    MembershipsReportView,
    PaymentsReportView,
    ReportsHomeView,
    TrainersReportView,
    VisitsReportView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('reports/', ReportsHomeView.as_view(), name='reports_home'),
    path('reports/clients/', ClientsReportView.as_view(), name='clients_report'),
    path('reports/memberships/', MembershipsReportView.as_view(), name='memberships_report'),
    path('reports/visits/', VisitsReportView.as_view(), name='visits_report'),
    path('reports/payments/', PaymentsReportView.as_view(), name='payments_report'),
    path('reports/trainers/', TrainersReportView.as_view(), name='trainers_report'),
]