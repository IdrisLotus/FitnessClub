from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView, View

from accounts.permissions import is_admin, is_trainer
from trainers.models import Trainer

from .forms import ClassRegistrationForm, FitnessClassForm
from .models import ClassRegistration, FitnessClass
from .services import (
    cancel_class,
    cancel_registration,
    can_trainer_access_class,
    can_user_create_class,
    complete_class,
    get_available_places,
    get_trainer_for_user,
    mark_registration_missed,
    mark_registration_visited,
    register_client_to_class,
)


def get_validation_error_message(error):
    if hasattr(error, 'messages') and error.messages:
        return ' '.join(error.messages)

    if hasattr(error, 'message'):
        return error.message

    return str(error)


class FitnessClassListView(LoginRequiredMixin, ListView):
    model = FitnessClass
    template_name = 'schedule/class_list.html'
    context_object_name = 'classes'
    paginate_by = 20

    def get_queryset(self):
        queryset = FitnessClass.objects.select_related('trainer').order_by(
            'class_date',
            'start_time',
        )

        if is_trainer(self.request.user) and not is_admin(self.request.user):
            trainer = get_trainer_for_user(self.request.user)

            if trainer:
                queryset = queryset.filter(trainer=trainer)
            else:
                queryset = FitnessClass.objects.none()

        date = self.request.GET.get('date', '').strip()
        trainer_id = self.request.GET.get('trainer', '').strip()
        status = self.request.GET.get('status', '').strip()
        query = self.request.GET.get('q', '').strip()

        if date:
            queryset = queryset.filter(class_date=date)

        if trainer_id and (self.request.user.is_superuser or is_admin(self.request.user)):
            queryset = queryset.filter(trainer_id=trainer_id)

        if status:
            queryset = queryset.filter(status=status)

        if query:
            queryset = queryset.filter(title__icontains=query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['trainers'] = Trainer.objects.filter(status=Trainer.STATUS_ACTIVE).order_by('full_name')
        context['status_choices'] = FitnessClass.STATUS_CHOICES
        context['current_date'] = self.request.GET.get('date', '').strip()
        context['current_trainer'] = self.request.GET.get('trainer', '').strip()
        context['current_status'] = self.request.GET.get('status', '').strip()
        context['query'] = self.request.GET.get('q', '').strip()

        context['can_create_class'] = can_user_create_class(self.request.user)
        context['is_admin_user'] = self.request.user.is_superuser or is_admin(self.request.user)

        return context


class MyClassesView(LoginRequiredMixin, ListView):
    model = FitnessClass
    template_name = 'schedule/my_classes.html'
    context_object_name = 'classes'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.trainer = get_trainer_for_user(request.user)

        if not self.trainer:
            messages.error(request, 'Ваш аккаунт не связан с карточкой тренера.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return FitnessClass.objects.filter(
            trainer=self.trainer
        ).order_by('class_date', 'start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['trainer'] = self.trainer
        context['can_create_class'] = True
        return context


class FitnessClassDetailView(LoginRequiredMixin, DetailView):
    model = FitnessClass
    template_name = 'schedule/class_detail.html'
    context_object_name = 'fitness_class'

    def dispatch(self, request, *args, **kwargs):
        fitness_class = self.get_object()

        if not can_trainer_access_class(request.user, fitness_class):
            messages.error(request, 'У вас нет доступа к этому занятию.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fitness_class = self.object

        context['registrations'] = (
            ClassRegistration.objects
            .filter(fitness_class=fitness_class)
            .select_related('client')
            .order_by('client__full_name')
        )

        context['available_places'] = get_available_places(fitness_class)
        context['can_manage_class'] = can_trainer_access_class(self.request.user, fitness_class)
        context['can_register_clients'] = (
            can_trainer_access_class(self.request.user, fitness_class)
            and fitness_class.status != FitnessClass.STATUS_CANCELLED
        )

        return context


class FitnessClassCreateView(LoginRequiredMixin, CreateView):
    model = FitnessClass
    form_class = FitnessClassForm
    template_name = 'schedule/class_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_user_create_class(request.user):
            messages.error(request, 'У вас нет прав для создания занятия.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if is_trainer(self.request.user) and not is_admin(self.request.user) and not self.request.user.is_superuser:
            trainer = get_trainer_for_user(self.request.user)

            if not trainer:
                form.add_error(None, 'Ваш аккаунт не связан с карточкой тренера.')
                return self.form_invalid(form)

            form.instance.trainer = trainer

        messages.success(self.request, 'Занятие успешно создано.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('schedule:detail', kwargs={'pk': self.object.pk})


class FitnessClassUpdateView(LoginRequiredMixin, UpdateView):
    model = FitnessClass
    form_class = FitnessClassForm
    template_name = 'schedule/class_form.html'

    def dispatch(self, request, *args, **kwargs):
        fitness_class = self.get_object()

        if not can_trainer_access_class(request.user, fitness_class):
            messages.error(request, 'У вас нет прав для редактирования этого занятия.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if is_trainer(self.request.user) and not is_admin(self.request.user) and not self.request.user.is_superuser:
            trainer = get_trainer_for_user(self.request.user)

            if trainer:
                form.instance.trainer = trainer

        messages.success(self.request, 'Занятие успешно обновлено.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('schedule:detail', kwargs={'pk': self.object.pk})


class FitnessClassCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fitness_class = get_object_or_404(FitnessClass, pk=pk)

        if not can_trainer_access_class(request.user, fitness_class):
            messages.error(request, 'У вас нет прав для отмены этого занятия.')
            raise PermissionDenied

        try:
            cancel_class(fitness_class)
            messages.success(request, 'Занятие успешно отменено.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('schedule:detail', pk=fitness_class.pk)


class FitnessClassCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        fitness_class = get_object_or_404(FitnessClass, pk=pk)

        try:
            complete_class(fitness_class, request.user)
            messages.success(request, 'Занятие отмечено как проведенное.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('schedule:detail', pk=fitness_class.pk)


class ClassRegistrationCreateView(LoginRequiredMixin, FormView):
    form_class = ClassRegistrationForm
    template_name = 'schedule/registration_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.fitness_class = get_object_or_404(FitnessClass, pk=kwargs['class_id'])

        if not can_trainer_access_class(request.user, self.fitness_class):
            messages.error(request, 'У вас нет прав для записи клиентов на это занятие.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['fitness_class'] = self.fitness_class
        kwargs['user'] = self.request.user

        # Важно: передаем занятие в instance до form.is_valid(),
        # иначе ModelForm вызывает full_clean() без fitness_class.
        kwargs['instance'] = ClassRegistration(
            fitness_class=self.fitness_class,
        )

        return kwargs

    def form_valid(self, form):
        try:
            register_client_to_class(
                fitness_class=self.fitness_class,
                client=form.cleaned_data['client'],
            )
        except ValidationError as error:
            form.add_error(None, get_validation_error_message(error))
            return self.form_invalid(form)

        messages.success(self.request, 'Клиент успешно записан на занятие.')
        return redirect('schedule:detail', pk=self.fitness_class.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fitness_class'] = self.fitness_class
        context['available_places'] = get_available_places(self.fitness_class)
        return context


class ClassRegistrationCancelView(LoginRequiredMixin, TemplateView):
    template_name = 'schedule/registration_confirm_cancel.html'

    def dispatch(self, request, *args, **kwargs):
        self.registration = get_object_or_404(
            ClassRegistration.objects.select_related('fitness_class', 'client'),
            pk=kwargs['pk'],
        )

        if not can_trainer_access_class(request.user, self.registration.fitness_class):
            messages.error(request, 'У вас нет прав для отмены этой записи.')
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['registration'] = self.registration
        return context

    def post(self, request, *args, **kwargs):
        try:
            cancel_registration(self.registration)
            messages.success(request, 'Запись клиента отменена.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('schedule:detail', pk=self.registration.fitness_class.pk)


class ClassRegistrationVisitedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        registration = get_object_or_404(
            ClassRegistration.objects.select_related('fitness_class', 'client'),
            pk=pk,
        )

        if not can_trainer_access_class(request.user, registration.fitness_class):
            messages.error(request, 'У вас нет прав для изменения этой записи.')
            raise PermissionDenied

        try:
            mark_registration_visited(registration, request.user)
            messages.success(request, 'Клиент отмечен как посетивший занятие. Посещение списано из абонемента.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('schedule:detail', pk=registration.fitness_class.pk)

class ClassRegistrationMissedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        registration = get_object_or_404(
            ClassRegistration.objects.select_related('fitness_class', 'client'),
            pk=pk,
        )

        if not can_trainer_access_class(request.user, registration.fitness_class):
            messages.error(request, 'У вас нет прав для изменения этой записи.')
            raise PermissionDenied

        try:
            mark_registration_missed(registration)
            messages.success(request, 'Клиент отмечен как не пришедший.')
        except ValidationError as error:
            messages.error(request, get_validation_error_message(error))

        return redirect('schedule:detail', pk=registration.fitness_class.pk)