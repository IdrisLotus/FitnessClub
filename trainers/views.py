from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from accounts.permissions import AdminRequiredMixin, is_admin, is_trainer

from .forms import TrainerClientAssignmentForm, TrainerForm
from .models import Trainer, TrainerClientAssignment


def get_current_trainer(user):
    if not user.is_authenticated:
        return None

    return Trainer.objects.filter(user=user).first()


def can_access_trainer(user, trainer):
    if is_admin(user) or user.is_superuser:
        return True

    current_trainer = get_current_trainer(user)

    return current_trainer and current_trainer.pk == trainer.pk


def get_validation_error_message(error):
    if hasattr(error, 'messages') and error.messages:
        return ' '.join(error.messages)

    if hasattr(error, 'message'):
        return error.message

    return str(error)


class TrainerListView(LoginRequiredMixin, ListView):
    model = Trainer
    template_name = 'trainers/trainer_list.html'
    context_object_name = 'trainers'
    paginate_by = 10

    def get_queryset(self):
        queryset = Trainer.objects.select_related('user').order_by('full_name')

        if is_trainer(self.request.user) and not is_admin(self.request.user):
            current_trainer = get_current_trainer(self.request.user)

            if current_trainer:
                queryset = queryset.filter(pk=current_trainer.pk)
            else:
                queryset = Trainer.objects.none()

        query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()

        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(email__icontains=query)
                | Q(specialization__icontains=query)
            )

        if status:
            queryset = queryset.filter(status=status)

        return queryset.annotate(
            assigned_clients_count=Count('client_assignments', distinct=True),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        context['selected_status'] = self.request.GET.get('status', '').strip()
        context['status_choices'] = Trainer.STATUS_CHOICES
        context['is_admin_user'] = is_admin(self.request.user)
        return context


class TrainerDetailView(LoginRequiredMixin, DetailView):
    model = Trainer
    template_name = 'trainers/trainer_detail.html'
    context_object_name = 'trainer'

    def dispatch(self, request, *args, **kwargs):
        trainer = self.get_object()

        if not can_access_trainer(request.user, trainer):
            messages.error(request, 'У вас нет доступа к этому тренеру.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trainer = self.object

        context['is_admin_user'] = is_admin(self.request.user)
        context['assigned_clients'] = (
            TrainerClientAssignment.objects
            .filter(trainer=trainer)
            .select_related('client', 'assigned_by')
            .order_by('client__full_name')
        )

        try:
            from schedule.models import FitnessClass

            today = timezone.localdate()

            context['planned_classes'] = (
                FitnessClass.objects
                .filter(trainer=trainer, status='planned', class_date__gte=today)
                .order_by('class_date', 'start_time')[:10]
            )

            context['completed_classes'] = (
                FitnessClass.objects
                .filter(trainer=trainer, status='completed')
                .order_by('-class_date', '-start_time')[:10]
            )
        except Exception:
            context['planned_classes'] = []
            context['completed_classes'] = []

        return context


class TrainerCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Trainer
    form_class = TrainerForm
    template_name = 'trainers/trainer_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Тренер успешно добавлен.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('trainers:detail', kwargs={'pk': self.object.pk})


class TrainerUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Trainer
    form_class = TrainerForm
    template_name = 'trainers/trainer_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Данные тренера успешно обновлены.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('trainers:detail', kwargs={'pk': self.object.pk})


class TrainerDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Trainer
    template_name = 'trainers/trainer_confirm_delete.html'
    context_object_name = 'trainer'
    success_url = reverse_lazy('trainers:list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.status == Trainer.STATUS_DISMISSED:
            messages.warning(request, 'Тренер уже имеет статус «Уволен».')
        else:
            self.object.status = Trainer.STATUS_DISMISSED
            self.object.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Тренер переведен в статус «Уволен».')

        return redirect(self.success_url)


class TrainerClientsView(LoginRequiredMixin, TemplateView):
    template_name = 'trainers/trainer_clients.html'

    def get_trainer(self):
        trainer_id = self.kwargs.get('pk')

        if trainer_id:
            trainer = get_object_or_404(Trainer, pk=trainer_id)
        else:
            trainer = get_current_trainer(self.request.user)

            if not trainer:
                messages.error(self.request, 'Ваш аккаунт не связан с карточкой тренера.')
                raise PermissionDenied

        if not can_access_trainer(self.request.user, trainer):
            messages.error(self.request, 'У вас нет доступа к клиентам этого тренера.')
            raise PermissionDenied

        return trainer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trainer = self.get_trainer()

        assignments = (
            TrainerClientAssignment.objects
            .filter(trainer=trainer)
            .select_related('client', 'assigned_by')
            .order_by('client__full_name')
        )

        context['trainer'] = trainer
        context['assignments'] = assignments
        context['is_admin_user'] = is_admin(self.request.user)
        context['is_own_trainer_page'] = trainer.user_id == self.request.user.id

        return context


class TrainerClientAddView(LoginRequiredMixin, FormView):
    form_class = TrainerClientAssignmentForm
    template_name = 'trainers/trainer_client_form.html'

    def dispatch(self, request, *args, **kwargs):
        trainer_id = kwargs.get('pk')

        if trainer_id:
            self.trainer = get_object_or_404(Trainer, pk=trainer_id)
        else:
            self.trainer = get_current_trainer(request.user)

            if not self.trainer:
                messages.error(request, 'Ваш аккаунт не связан с карточкой тренера.')
                raise PermissionDenied

        if not can_access_trainer(request.user, self.trainer):
            messages.error(request, 'У вас нет доступа к этому действию.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['trainer'] = self.trainer

        # Важно: передаем trainer в instance до form.is_valid(),
        # чтобы ModelForm не падала на проверке обязательного поля trainer.
        kwargs['instance'] = TrainerClientAssignment(
            trainer=self.trainer,
            assigned_by=self.request.user,
        )

        return kwargs

    def form_valid(self, form):
        assignment = form.save(commit=False)
        assignment.trainer = self.trainer
        assignment.assigned_by = self.request.user

        try:
            assignment.full_clean()
            assignment.save()
        except IntegrityError:
            form.add_error(None, 'Этот клиент уже закреплен за данным тренером.')
            return self.form_invalid(form)
        except ValidationError as error:
            form.add_error(None, get_validation_error_message(error))
            return self.form_invalid(form)

        messages.success(
            self.request,
            f'Клиент {assignment.client.full_name} закреплен за тренером {self.trainer.full_name}.',
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.kwargs.get('pk'):
            return reverse('trainers:clients', kwargs={'pk': self.trainer.pk})

        return reverse('trainers:my_clients')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['trainer'] = self.trainer
        return context


class TrainerClientRemoveView(LoginRequiredMixin, TemplateView):
    template_name = 'trainers/trainer_client_confirm_remove.html'

    def dispatch(self, request, *args, **kwargs):
        self.assignment = get_object_or_404(
            TrainerClientAssignment.objects.select_related('trainer', 'client'),
            pk=kwargs['assignment_pk'],
        )

        if not can_access_trainer(request.user, self.assignment.trainer):
            messages.error(request, 'У вас нет доступа к этому действию.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignment'] = self.assignment
        context['trainer'] = self.assignment.trainer
        return context

    def post(self, request, *args, **kwargs):
        trainer = self.assignment.trainer
        client_name = self.assignment.client.full_name

        self.assignment.delete()

        messages.success(
            request,
            f'Клиент {client_name} откреплен от тренера {trainer.full_name}.',
        )

        if kwargs.get('pk'):
            return redirect('trainers:clients', pk=trainer.pk)

        return redirect('trainers:my_clients')


class TrainerMyClassesView(LoginRequiredMixin, TemplateView):
    template_name = 'trainers/my_classes.html'

    def dispatch(self, request, *args, **kwargs):
        self.trainer = get_current_trainer(request.user)

        if not self.trainer:
            messages.error(request, 'Ваш аккаунт не связан с карточкой тренера.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from schedule.models import FitnessClass

        context = super().get_context_data(**kwargs)

        today = timezone.localdate()

        planned_classes = (
            FitnessClass.objects
            .filter(trainer=self.trainer, status='planned')
            .order_by('class_date', 'start_time')
        )

        completed_classes = (
            FitnessClass.objects
            .filter(trainer=self.trainer, status='completed')
            .order_by('-class_date', '-start_time')
        )

        context['trainer'] = self.trainer
        context['today'] = today
        context['planned_classes'] = planned_classes
        context['completed_classes'] = completed_classes

        return context