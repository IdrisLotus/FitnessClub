from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import UserProfile


def get_user_role(user):
    """
    Безопасно возвращает роль пользователя.

    Важно:
    - superuser считается администратором;
    - поддерживается user.userprofile;
    - дополнительно поддерживается user.profile, если в модели задан related_name='profile';
    - если профиль отсутствует, возвращается None.
    """
    if not user or not user.is_authenticated:
        return None

    if user.is_superuser:
        return UserProfile.ROLE_ADMIN

    profile = getattr(user, 'userprofile', None)

    if profile is None:
        profile = getattr(user, 'profile', None)

    if profile is None:
        return None

    return profile.role


def is_admin(user):
    return get_user_role(user) == UserProfile.ROLE_ADMIN


def is_trainer(user):
    return get_user_role(user) == UserProfile.ROLE_TRAINER


def is_manager(user):
    return get_user_role(user) == UserProfile.ROLE_MANAGER


def is_admin_or_manager(user):
    return get_user_role(user) in [
        UserProfile.ROLE_ADMIN,
        UserProfile.ROLE_MANAGER,
    ]


def user_has_role(user, roles):
    """
    Проверяет, входит ли роль пользователя в список разрешенных ролей.

    Пример:
    user_has_role(request.user, ['admin', 'manager'])
    """
    if isinstance(roles, str):
        roles = [roles]

    return get_user_role(user) in roles


def role_required(roles):
    """
    Универсальный декоратор проверки роли.

    Использование:
    @role_required(['admin', 'manager'])
    def some_view(request):
        ...
    """
    if isinstance(roles, str):
        roles = [roles]

    def check_role(user):
        return user.is_authenticated and user_has_role(user, roles)

    return user_passes_test(check_role, login_url='accounts:login')


def admin_required(view_func):
    """
    Декоратор для доступа только администратора.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not is_admin(request.user):
            messages.error(request, 'У вас нет прав для выполнения этого действия.')
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


def trainer_required(view_func):
    """
    Декоратор для доступа только тренера.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not is_trainer(request.user):
            messages.error(request, 'У вас нет прав для выполнения этого действия.')
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_or_manager_required(view_func):
    """
    Декоратор для доступа администратора или руководителя.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not is_admin_or_manager(request.user):
            messages.error(request, 'У вас нет прав для выполнения этого действия.')
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


class RoleRequiredMixin(UserPassesTestMixin):
    """
    Универсальный mixin для class-based views.

    Использование:
    class SomeView(RoleRequiredMixin, View):
        allowed_roles = ['admin', 'manager']
    """
    allowed_roles = []

    def test_func(self):
        return self.request.user.is_authenticated and user_has_role(
            self.request.user,
            self.allowed_roles,
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('accounts:login')

        messages.error(self.request, 'У вас нет прав для доступа к этой странице.')
        raise PermissionDenied


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserProfile.ROLE_ADMIN]


class TrainerRequiredMixin(RoleRequiredMixin):
    allowed_roles = [UserProfile.ROLE_TRAINER]


class AdminOrManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = [
        UserProfile.ROLE_ADMIN,
        UserProfile.ROLE_MANAGER,
    ]