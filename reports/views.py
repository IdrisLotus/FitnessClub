from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.permissions import AdminOrManagerRequiredMixin, get_user_role
from clients.models import Client
from memberships.models import ClientMembership
from payments.models import Payment
from schedule.models import ClassRegistration, FitnessClass
from trainers.models import Trainer
from visits.models import Visit


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.localdate()
        month_start = today.replace(day=1)
        soon_date = today + timedelta(days=7)

        role = get_user_role(self.request.user)
        context['role'] = role

        if role == 'trainer':
            trainer = Trainer.objects.filter(user=self.request.user).first()
            context['trainer'] = trainer

            if trainer:
                context['today_classes_count'] = FitnessClass.objects.filter(
                    trainer=trainer,
                    class_date=today,
                ).count()

                context['upcoming_classes'] = FitnessClass.objects.filter(
                    trainer=trainer,
                    class_date__gte=today,
                ).order_by('class_date', 'start_time')[:10]

                context['completed_classes_count'] = FitnessClass.objects.filter(
                    trainer=trainer,
                    status='completed',
                ).count()

                context['registered_clients_count'] = ClassRegistration.objects.filter(
                    fitness_class__trainer=trainer,
                    status__in=['registered', 'visited'],
                ).values('client').distinct().count()

            return context

        context['total_clients'] = Client.objects.count()
        context['active_clients'] = Client.objects.filter(status='active').count()
        context['active_memberships'] = ClientMembership.objects.filter(status='active').count()

        context['today_visits'] = Visit.objects.filter(
            status='active',
            visit_datetime__date=today,
        ).count()

        context['monthly_income'] = Payment.objects.filter(
            status='paid',
            payment_date__gte=month_start,
            payment_date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or 0

        context['today_classes'] = FitnessClass.objects.filter(
            class_date=today,
        ).count()

        context['expiring_memberships'] = ClientMembership.objects.select_related(
            'client',
            'membership_type',
        ).filter(
            status='active',
            end_date__gte=today,
            end_date__lte=soon_date,
        ).order_by('end_date')[:10]

        context['zero_visit_memberships'] = ClientMembership.objects.select_related(
            'client',
            'membership_type',
        ).filter(
            remaining_visits=0,
            status__in=['active', 'completed'],
        ).order_by('end_date')[:10]

        return context


class ReportsHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/reports_home.html'

    def dispatch(self, request, *args, **kwargs):
        role = get_user_role(request.user)

        if role == 'trainer':
            messages.error(request, 'Тренеру недоступны общие отчеты.')
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)


class ClientsReportView(LoginRequiredMixin, AdminOrManagerRequiredMixin, TemplateView):
    template_name = 'reports/clients_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        new_clients = Client.objects.all()

        if date_from:
            new_clients = new_clients.filter(registration_date__gte=date_from)

        if date_to:
            new_clients = new_clients.filter(registration_date__lte=date_to)

        context['date_from'] = date_from
        context['date_to'] = date_to
        context['total_clients'] = Client.objects.count()
        context['active_clients'] = Client.objects.filter(status='active').count()
        context['inactive_clients'] = Client.objects.filter(status='inactive').count()
        context['frozen_clients'] = Client.objects.filter(status='frozen').count()
        context['archived_clients'] = Client.objects.filter(status='archived').count()
        context['new_clients_count'] = new_clients.count()
        context['new_clients'] = new_clients.order_by('-registration_date')[:50]

        return context


class MembershipsReportView(LoginRequiredMixin, AdminOrManagerRequiredMixin, TemplateView):
    template_name = 'reports/memberships_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.localdate()
        soon_date = today + timedelta(days=7)

        context['active_memberships'] = ClientMembership.objects.filter(status='active').count()
        context['expired_memberships'] = ClientMembership.objects.filter(status='expired').count()
        context['completed_memberships'] = ClientMembership.objects.filter(status='completed').count()
        context['frozen_memberships'] = ClientMembership.objects.filter(status='frozen').count()
        context['cancelled_memberships'] = ClientMembership.objects.filter(status='cancelled').count()

        context['expiring_memberships'] = ClientMembership.objects.select_related(
            'client',
            'membership_type',
        ).filter(
            status='active',
            end_date__gte=today,
            end_date__lte=soon_date,
        ).order_by('end_date')[:50]

        return context


class VisitsReportView(LoginRequiredMixin, AdminOrManagerRequiredMixin, TemplateView):
    template_name = 'reports/visits_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        client_id = self.request.GET.get('client')

        visits = Visit.objects.select_related(
            'client',
            'membership',
        ).filter(status='active')

        if date_from:
            visits = visits.filter(visit_datetime__date__gte=date_from)

        if date_to:
            visits = visits.filter(visit_datetime__date__lte=date_to)

        if client_id:
            visits = visits.filter(client_id=client_id)

        context['date_from'] = date_from
        context['date_to'] = date_to
        context['selected_client'] = client_id
        context['clients'] = Client.objects.order_by('full_name')
        context['visits_count'] = visits.count()

        context['visits_by_day'] = (
            visits
            .annotate(day=TruncDate('visit_datetime'))
            .values('day')
            .annotate(total=Count('id'))
            .order_by('day')
        )

        context['visits'] = visits.order_by('-visit_datetime')[:100]

        return context


class PaymentsReportView(LoginRequiredMixin, AdminOrManagerRequiredMixin, TemplateView):
    template_name = 'reports/payments_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.localdate()
        month_start = today.replace(day=1)

        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        client_id = self.request.GET.get('client')

        payments = Payment.objects.select_related(
            'client',
            'membership',
        ).filter(status='paid')

        if date_from:
            payments = payments.filter(payment_date__gte=date_from)

        if date_to:
            payments = payments.filter(payment_date__lte=date_to)

        if client_id:
            payments = payments.filter(client_id=client_id)

        context['date_from'] = date_from
        context['date_to'] = date_to
        context['selected_client'] = client_id
        context['clients'] = Client.objects.order_by('full_name')

        context['total_amount'] = payments.aggregate(
            total=Sum('amount')
        )['total'] or 0

        context['payments_by_method'] = (
            payments
            .values('payment_method')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('payment_method')
        )

        context['monthly_income'] = Payment.objects.filter(
            status='paid',
            payment_date__gte=month_start,
            payment_date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or 0

        context['payments'] = payments.order_by('-payment_date')[:100]

        return context


class TrainersReportView(LoginRequiredMixin, AdminOrManagerRequiredMixin, TemplateView):
    template_name = 'reports/trainers_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['trainers'] = Trainer.objects.annotate(
            classes_count=Count(
                'fitness_classes',
                distinct=True,
            ),
            completed_classes_count=Count(
                'fitness_classes',
                filter=Q(fitness_classes__status='completed'),
                distinct=True,
            ),
            cancelled_classes_count=Count(
                'fitness_classes',
                filter=Q(fitness_classes__status='cancelled'),
                distinct=True,
            ),
            registered_clients_count=Count(
                'fitness_classes__registrations__client',
                filter=Q(
                    fitness_classes__registrations__status__in=[
                        'registered',
                        'visited',
                    ]
                ),
                distinct=True,
            ),
        ).order_by('full_name')

        return context