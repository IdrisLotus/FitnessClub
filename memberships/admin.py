from django.contrib import admin

from .models import ClientMembership, MembershipType


@admin.register(MembershipType)
class MembershipTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'duration_days',
        'visit_limit',
        'price',
        'is_active',
    )
    list_filter = (
        'is_active',
    )
    search_fields = (
        'name',
    )


@admin.register(ClientMembership)
class ClientMembershipAdmin(admin.ModelAdmin):
    list_display = (
        'client',
        'membership_type',
        'start_date',
        'end_date',
        'remaining_visits',
        'status',
    )
    list_filter = (
        'status',
        'start_date',
        'end_date',
    )
    search_fields = (
        'client__full_name',
        'membership_type__name',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )