from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin

from .models import Payment, DirectBankTransfer, Mutation, Checkout, Checkin


@admin.register(DirectBankTransfer)
class DirectBankTransferAdmin(PolymorphicChildModelAdmin):
    base_model = Payment


@admin.register(Payment)
class PaymentAdmin(PolymorphicParentModelAdmin):
    child_models = [DirectBankTransfer]
    list_display = ['name', 'account_name', 'account_number', 'balance']


@admin.register(Mutation)
class MutationAdmin(PolymorphicParentModelAdmin):
    child_models = [Checkout, Checkin]
    list_display = [
        'inner_id',
        'payment_account',
        'created_at',
        'flow',
        'amount',
        'balance',
        'is_verified',
    ]


@admin.register(Checkin)
class CheckinAdmin(PolymorphicChildModelAdmin):
    base_model = Mutation
    fields = [
        'content_type',
        'object_id',
        'account_name',
        'account_number',
        'provider_name',
        'amount',
        'payment_account',
        'transfer_receipt',
        'note',
        'is_verified',
    ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.payment_account.update()


@admin.register(Checkout)
class CheckoutAdmin(PolymorphicChildModelAdmin):
    base_model = Mutation
    fields = [
        'content_type',
        'object_id',
        'account_name',
        'account_number',
        'provider_name',
        'amount',
        'payment_account',
        'transfer_receipt',
        'note',
        'is_verified',
    ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.payment_account.update()
