from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from accounts.permissions import AdminRequiredMixin, is_admin
from clients.models import Client

from .forms import ClientMembershipForm, MembershipTypeForm
from .models import ClientMembership, MembershipType
from .services import (
    activate_membership,
    cancel_membership,
    create_client_membership,
    freeze_membership,
    update_membership_status,
)


class MembershipTypeListView(LoginRequiredMixin, ListView):
    model = MembershipType
    template_name = 'memberships/membership_type_list.html'
    context_object_name = 'membership_types'
    paginate_by = 10

    def get_queryset(self):
        queryset = MembershipType.objects.all().order_by('name')
        is_active = self.request.GET.get('is_active')

        if is_active == '1':
            queryset = queryset.filter(is_active=True)
        elif is_active == '0':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_is_active'] = self.request.GET.get('is_active', '')
        context['is_admin_user'] = is_admin(self.request.user)
        return context


class MembershipTypeCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = MembershipType
    form_class = MembershipTypeForm
    template_name = 'memberships/membership_type_form.html'
    success_url = reverse_lazy('memberships:type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Тип абонемента успешно создан.')
        return super().form_valid(form)


class MembershipTypeUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = MembershipType
    form_class = MembershipTypeForm
    template_name = 'memberships/membership_type_form.html'
    success_url = reverse_lazy('memberships:type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Тип абонемента успешно обновлен.')
        return super().form_valid(form)


class MembershipTypeDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = MembershipType
    template_name = 'memberships/membership_type_confirm_delete.html'
    context_object_name = 'membership_type'
    success_url = reverse_lazy('memberships:type_list')

    def post(self, request, *args, **kwargs):
        membership_type = self.get_object()

        if membership_type.client_memberships.exists():
            membership_type.is_active = False
            membership_type.save(update_fields=['is_active', 'updated_at'])
            messages.warning(
                request,
                'Тип абонемента уже используется, поэтому он был деактивирован, а не удален.',
            )
            return redirect(self.success_url)

        membership_type.delete()
        messages.success(request, 'Тип абонемента успешно удален.')
        return redirect(self.success_url)


class ClientMembershipCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = ClientMembership
    form_class = ClientMembershipForm
    template_name = 'memberships/client_membership_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.client = get_object_or_404(Client, pk=kwargs['client_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # Важно: клиент должен быть установлен до form.is_valid(),
        # иначе ModelForm вызывает full_clean() без client.
        kwargs['instance'] = ClientMembership(client=self.client)

        return kwargs

    def form_valid(self, form):
        membership_type = form.cleaned_data['membership_type']
        start_date = form.cleaned_data['start_date']

        try:
            create_client_membership(
                client=self.client,
                membership_type=membership_type,
                start_date=start_date,
            )
        except ValidationError as error:
            form.add_error(None, get_validation_error_message(error))
            return self.form_invalid(form)

        messages.success(
            self.request,
            f'Абонемент успешно назначен клиенту {self.client.full_name}.'
        )

        return redirect('clients:detail', pk=self.client.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        return context


class ClientMembershipDetailView(LoginRequiredMixin, DetailView):
    model = ClientMembership
    template_name = 'memberships/client_membership_detail.html'
    context_object_name = 'membership'

    def get_object(self, queryset=None):
        membership = super().get_object(queryset)

        try:
            update_membership_status(membership)
            membership.refresh_from_db()
        except ValidationError:
            pass

        return membership

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin_user'] = is_admin(self.request.user)
        return context


class ClientMembershipFreezeView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        membership = get_object_or_404(ClientMembership, pk=pk)

        try:
            freeze_membership(membership)
            messages.success(request, 'Абонемент успешно заморожен.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('memberships:client_membership_detail', pk=membership.pk)


class ClientMembershipActivateView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        membership = get_object_or_404(ClientMembership, pk=pk)

        try:
            activate_membership(membership)
            messages.success(request, 'Абонемент успешно активирован.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('memberships:client_membership_detail', pk=membership.pk)


class ClientMembershipCancelView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = ClientMembership
    template_name = 'memberships/client_membership_confirm_cancel.html'
    context_object_name = 'membership'

    def post(self, request, pk):
        membership = get_object_or_404(ClientMembership, pk=pk)

        try:
            cancel_membership(membership)
            messages.success(request, 'Абонемент успешно отменен.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('memberships:client_membership_detail', pk=membership.pk)


def get_validation_error_message(error):
    if hasattr(error, 'messages') and error.messages:
        return error.messages[0]

    if hasattr(error, 'message'):
        return error.message

    return str(error)