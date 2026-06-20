from django.urls import path

from .views import (
    ClientMembershipActivateView,
    ClientMembershipCancelView,
    ClientMembershipCreateView,
    ClientMembershipDetailView,
    ClientMembershipFreezeView,
    MembershipTypeCreateView,
    MembershipTypeDeleteView,
    MembershipTypeListView,
    MembershipTypeUpdateView,
)

app_name = 'memberships'

urlpatterns = [
    path(
        'membership-types/',
        MembershipTypeListView.as_view(),
        name='type_list',
    ),
    path(
        'membership-types/create/',
        MembershipTypeCreateView.as_view(),
        name='type_create',
    ),
    path(
        'membership-types/<int:pk>/edit/',
        MembershipTypeUpdateView.as_view(),
        name='type_edit',
    ),
    path(
        'membership-types/<int:pk>/delete/',
        MembershipTypeDeleteView.as_view(),
        name='type_delete',
    ),

    path(
        'clients/<int:client_id>/memberships/create/',
        ClientMembershipCreateView.as_view(),
        name='client_membership_create',
    ),
    path(
        'memberships/<int:pk>/',
        ClientMembershipDetailView.as_view(),
        name='client_membership_detail',
    ),
    path(
        'memberships/<int:pk>/freeze/',
        ClientMembershipFreezeView.as_view(),
        name='client_membership_freeze',
    ),
    path(
        'memberships/<int:pk>/activate/',
        ClientMembershipActivateView.as_view(),
        name='client_membership_activate',
    ),
    path(
        'memberships/<int:pk>/cancel/',
        ClientMembershipCancelView.as_view(),
        name='client_membership_cancel',
    ),
]