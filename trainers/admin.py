from django.contrib import admin

from .models import Trainer, TrainerClientAssignment


class TrainerClientAssignmentInline(admin.TabularInline):
    model = TrainerClientAssignment
    extra = 0
    autocomplete_fields = ('client', 'assigned_by')
    readonly_fields = ('assigned_at',)


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'phone',
        'email',
        'specialization',
        'experience_years',
        'status',
    )
    list_filter = (
        'status',
        'specialization',
    )
    search_fields = (
        'full_name',
        'phone',
        'email',
        'specialization',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    inlines = [
        TrainerClientAssignmentInline,
    ]


@admin.register(TrainerClientAssignment)
class TrainerClientAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'trainer',
        'client',
        'assigned_by',
        'assigned_at',
    )
    list_filter = (
        'trainer',
        'assigned_at',
    )
    search_fields = (
        'trainer__full_name',
        'client__full_name',
        'client__phone',
        'client__email',
    )
    readonly_fields = (
        'assigned_at',
    )
    autocomplete_fields = (
        'trainer',
        'client',
        'assigned_by',
    )