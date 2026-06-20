from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'client',
        'membership',
        'amount',
        'payment_method',
        'payment_date',
        'status',
        'created_by',
    )
    list_filter = (
        'payment_method',
        'status',
        'payment_date',
    )
    search_fields = (
        'client__full_name',
    )
    readonly_fields = (
        'created_by',
        'created_at',
        'updated_at',
    )