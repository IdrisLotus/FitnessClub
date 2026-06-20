from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, ListView, TemplateView

from accounts.permissions import AdminRequiredMixin
from clients.models import Client

from .forms import PaymentForm
from .models import Payment
from .services import cancel_payment, create_payment


def get_validation_error_message(error):
    if hasattr(error, 'messages') and error.messages:
        return ' '.join(error.messages)

    if hasattr(error, 'message'):
        return error.message

    return str(error)


class PaymentListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_base_queryset(self):
        queryset = Payment.objects.select_related(
            'client',
            'membership',
            'membership__membership_type',
            'created_by',
        ).order_by('-payment_date', '-created_at')

        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        client_id = self.request.GET.get('client', '').strip()
        payment_method = self.request.GET.get('payment_method', '').strip()
        status = self.request.GET.get('status', '').strip()

        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_queryset(self):
        return self.get_base_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filtered_queryset = self.get_base_queryset()

        total_amount = filtered_queryset.filter(
            status=Payment.STATUS_PAID,
        ).aggregate(
            total=Sum('amount'),
        )['total'] or 0

        context['clients'] = Client.objects.order_by('full_name')
        context['method_choices'] = Payment.METHOD_CHOICES
        context['status_choices'] = Payment.STATUS_CHOICES

        context['current_date_from'] = self.request.GET.get('date_from', '').strip()
        context['current_date_to'] = self.request.GET.get('date_to', '').strip()
        context['current_client'] = self.request.GET.get('client', '').strip()
        context['current_payment_method'] = self.request.GET.get('payment_method', '').strip()
        context['current_status'] = self.request.GET.get('status', '').strip()

        context['total_amount'] = total_amount

        return context


class PaymentCreateView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.client = get_object_or_404(Client, pk=kwargs['client_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['client'] = self.client
        return kwargs

    def form_valid(self, form):
        try:
            create_payment(
                client=self.client,
                membership=form.cleaned_data.get('membership'),
                amount=form.cleaned_data['amount'],
                payment_date=form.cleaned_data['payment_date'],
                payment_method=form.cleaned_data['payment_method'],
                comment=form.cleaned_data.get('comment', ''),
                user=self.request.user,
            )
        except ValidationError as error:
            form.add_error(None, get_validation_error_message(error))
            return self.form_invalid(form)

        messages.success(
            self.request,
            f'Оплата для клиента {self.client.full_name} успешно добавлена.'
        )
        return redirect('clients:detail', pk=self.client.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        return context


class PaymentCancelView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'payments/payment_confirm_cancel.html'

    def dispatch(self, request, *args, **kwargs):
        self.payment = get_object_or_404(
            Payment.objects.select_related(
                'client',
                'membership',
                'membership__membership_type',
            ),
            pk=kwargs['pk'],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment'] = self.payment
        return context

    def post(self, request, *args, **kwargs):
        try:
            cancel_payment(self.payment)
        except ValidationError as error:
            messages.warning(request, get_validation_error_message(error))
            return redirect('payments:list')

        messages.success(request, 'Оплата успешно отменена.')
        return redirect('payments:list')