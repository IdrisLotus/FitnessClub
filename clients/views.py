from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from trainers.models import TrainerClientAssignment
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.permissions import AdminRequiredMixin
from memberships.models import ClientMembership
from payments.models import Payment
from visits.models import Visit

from .forms import ClientForm
from .models import Client


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_queryset(self):
        queryset = Client.objects.all().order_by('full_name')

        query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()

        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(email__icontains=query)
            )

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['query'] = self.request.GET.get('q', '').strip()
        context['selected_status'] = self.request.GET.get('status', '').strip()

        if hasattr(Client, 'Status'):
            context['status_choices'] = Client.Status.choices
        else:
            context['status_choices'] = getattr(Client, 'STATUS_CHOICES', [])

        return context


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object

        context['current_membership'] = (
            ClientMembership.objects
            .filter(client=client, status='active')
            .select_related('membership_type')
            .order_by('-start_date')
            .first()
        )

        context['latest_visits'] = (
            Visit.objects
            .filter(client=client)
            .select_related('membership')
            .order_by('-visit_datetime')[:5]
        )

        context['latest_payments'] = (
            Payment.objects
            .filter(client=client)
            .select_related('membership')
            .order_by('-payment_date', '-created_at')[:5]
        )

        context['trainer_assignments'] = (
            TrainerClientAssignment.objects
            .filter(client=client)
            .select_related('trainer', 'assigned_by')
            .order_by('trainer__full_name')
        )

        return context


class ClientCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    context_object_name = 'client'

    def form_valid(self, form):
        messages.success(self.request, 'Клиент успешно добавлен.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clients:detail', kwargs={'pk': self.object.pk})


class ClientUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    context_object_name = 'client'

    def form_valid(self, form):
        messages.success(self.request, 'Данные клиента успешно обновлены.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clients:detail', kwargs={'pk': self.object.pk})


class ClientDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Client
    template_name = 'clients/client_confirm_delete.html'
    context_object_name = 'client'
    success_url = reverse_lazy('clients:list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        archived_status = 'archived'

        if hasattr(Client, 'Status'):
            archived_status = Client.Status.ARCHIVED

        if self.object.status == archived_status:
            messages.warning(request, 'Клиент уже находится в архиве.')
        else:
            self.object.status = archived_status
            self.object.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Клиент успешно перенесен в архив.')

        return redirect(self.success_url)