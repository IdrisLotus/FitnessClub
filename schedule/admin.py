from django.contrib import admin

from .models import ClassRegistration, FitnessClass


@admin.register(FitnessClass)
class FitnessClassAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'trainer',
        'class_date',
        'start_time',
        'end_time',
        'capacity',
        'status',
    )
    list_filter = (
        'status',
        'class_date',
        'trainer',
    )
    search_fields = (
        'title',
        'trainer__full_name',
    )


@admin.register(ClassRegistration)
class ClassRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'fitness_class',
        'client',
        'registration_date',
        'status',
    )
    list_filter = (
        'status',
        'registration_date',
    )
    search_fields = (
        'fitness_class__title',
        'client__full_name',
    )