from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'phone',
        'email',
        'status',
        'registration_date',
        'created_at',
    )
    list_filter = (
        'status',
        'gender',
        'registration_date',
    )
    search_fields = (
        'full_name',
        'phone',
        'email',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )