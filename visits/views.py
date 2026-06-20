from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, ListView, TemplateView

from accounts.permissions import AdminRequiredMixin
from clients.models import Client

from .forms import VisitForm
from .models import Visit
from .services import cancel_visit, mark_client_visit


def get_validation_error_message(error):
    if hasattr(error, 'messages') and error.messages:
        return ' '.join(error.messages)

    if hasattr(error, 'message'):
        return error.message

    return str(error)


class VisitListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Visit
    template_name = 'visits/visit_list.html'
    context_object_name = 'visits'
    paginate_by = 20

    def get_queryset(self):
        queryset = Visit.objects.select_related(
            'client',
            'membership',
            'membership__membership_type',
            'fitness_class',
            'created_by',
        ).order_by('-visit_datetime')

        date = self.request.GET.get('date', '').strip()
        client_id = self.request.GET.get('client', '').strip()
        status = self.request.GET.get('status', '').strip()

        if date:
            queryset = queryset.filter(visit_datetime__date=date)

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clients'] = Client.objects.order_by('full_name')
        context['status_choices'] = Visit.STATUS_CHOICES
        context['current_date'] = self.request.GET.get('date', '').strip()
        context['current_client'] = self.request.GET.get('client', '').strip()
        context['current_status'] = self.request.GET.get('status', '').strip()
        return context


class VisitCreateView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    form_class = VisitForm
    template_name = 'visits/visit_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.client = get_object_or_404(Client, pk=kwargs['client_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            mark_client_visit(
                client=self.client,
                user=self.request.user,
                comment=form.cleaned_data.get('comment', ''),
            )
        except ValidationError as error:
            form.add_error(None, get_validation_error_message(error))
            return self.form_invalid(form)

        messages.success(
            self.request,
            f'Посещение клиента {self.client.full_name} успешно отмечено.'
        )
        return redirect('clients:detail', pk=self.client.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        return context


class VisitCancelView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'visits/visit_confirm_cancel.html'

    def dispatch(self, request, *args, **kwargs):
        self.visit = get_object_or_404(
            Visit.objects.select_related(
                'client',
                'membership',
                'membership__membership_type',
            ),
            pk=kwargs['pk'],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['visit'] = self.visit
        return context

    def post(self, request, *args, **kwargs):
        try:
            cancel_visit(self.visit)
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))
            return redirect('visits:list')

        messages.success(request, 'Посещение успешно отменено.')
        return redirect('visits:list')