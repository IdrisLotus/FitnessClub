from django.contrib import admin

from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = (
        'client',
        'membership',
        'fitness_class',
        'visit_datetime',
        'status',
        'created_by',
    )
    list_filter = (
        'status',
        'visit_datetime',
        'fitness_class',
    )
    search_fields = (
        'client__full_name',
        'fitness_class__title',
    )
    readonly_fields = (
        'created_by',
    )