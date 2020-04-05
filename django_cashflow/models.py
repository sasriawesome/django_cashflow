import uuid
from django.db import models
from django.utils import translation, timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from polymorphic.models import PolymorphicModel

from django_numerators.models import NumeratorMixin

_ = translation.ugettext_lazy


class Payment(PolymorphicModel):
    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        verbose_name='uuid')
    checkin = models.BooleanField(
        default=True, verbose_name=_('Check In'))
    checkout = models.BooleanField(
        default=True, verbose_name=_('Check Out'))
    name = models.CharField(
        max_length=255, verbose_name=_('Name'))
    account_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=50)
    created_at = models.DateTimeField(
        default=timezone.now, editable=False)
    modified_at = models.DateTimeField(
        default=timezone.now, editable=False)
    balance = models.DecimalField(
        default=0,
        max_digits=15,
        decimal_places=2,
        editable=False,
        verbose_name=_("Balance"))

    def update(self):
        self.modified_at = timezone.now()
        self.save()

    def __str__(self):
        return self.name


class DirectBankTransfer(Payment):
    class Meta:
        verbose_name = _("Direct Bank Transfer")
        verbose_name_plural = _("Direct Bank Transfers")

    bank_name = models.CharField(max_length=150)
    branch_office = models.CharField(null=True, blank=True, max_length=150)

    def __str__(self):
        return self.bank_name


class Mutation(NumeratorMixin, PolymorphicModel):
    class Meta:
        verbose_name = _("Mutation")
        verbose_name_plural = _("Mutations")

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        verbose_name='uuid')
    flow = models.CharField(
        max_length=3,
        editable=False,
        choices=(('IN', 'In'), ('OUT', 'Out')),
        default='IN', verbose_name=_('Flow'))
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name='checkouts',
        verbose_name=_("Owner"))
    payment_account = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='mutations',
        verbose_name=_('Payment Account'))

    transfer_receipt = models.ImageField(
        null=True, blank=True,
        verbose_name=_("Transfer receipt"))

    amount = models.DecimalField(
        default=10000, max_digits=15, decimal_places=0,
        validators=[MinValueValidator(10000)],
        verbose_name=_("Amount"),
        help_text=_("Donation amount to be sent"))
    old_balance = models.DecimalField(
        default=0,
        max_digits=15,
        decimal_places=2,
        editable=False,
        verbose_name=_("Balance"))
    balance = models.DecimalField(
        default=0,
        max_digits=15,
        decimal_places=2,
        editable=False,
        verbose_name=_("Balance"))
    note = models.TextField(
        max_length=500,
        null=True, blank=True,
        verbose_name=_("Note"),
        help_text=_('Need help? please tell us.'))

    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(
        null=True, blank=True,
        editable=False,
        verbose_name=_("Verified at"))
    created_at = models.DateTimeField(
        default=timezone.now, editable=False)

    def __str__(self):
        return self.inner_id

    def get_reference(self):
        """Return the object represented by this mutation entry."""
        instance = self.get_real_instance()
        return instance.content_type.get_object_for_this_type(pk=instance.object_id)

    def get_amount(self):
        raise NotImplementedError

    def increase_balance(self):
        self.balance = self.payment_account.balance + self.amount
        return self.balance

    def decrease_balance(self):
        self.balance = self.payment_account.balance - self.amount
        return self.balance

    def calculate_balance(self):
        return {'IN': self.increase_balance, 'OUT': self.decrease_balance}[self.flow]()

    def save(self, *args, **kwargs):
        self.old_balance = self.payment_account.balance
        self.amount = self.get_amount()
        self.calculate_balance()
        super().save(*args, **kwargs)


class Checkout(Mutation):
    class Meta:
        verbose_name = _("Checkout")
        verbose_name_plural = _("Checkouts")

    account_name = models.CharField(
        max_length=255,
        verbose_name=_("Account Name"),
        help_text=_('Destination account/holder name.'))
    account_number = models.CharField(
        max_length=255,
        verbose_name=_("Account Number"),
        help_text=_('Destination account number.'))
    provider_name = models.CharField(
        max_length=255,
        verbose_name=_("Provider name"),
        help_text=_('Destination provider. (Bank Mandiri or Gopay)'))
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        limit_choices_to={'model__in': ['withdraw']},
        verbose_name=_('reference type'),
        blank=True, null=True,
    )
    object_id = models.CharField(_('reference id'), max_length=100, blank=True, null=True)

    def get_amount(self):
        return self.amount

    def __str__(self):
        return "{} / {}".format(self.inner_id, self.account_name)

    def save(self, *args, **kwargs):
        self.flow = 'OUT'
        super().save(*args, kwargs)


class Checkin(Mutation):
    class Meta:
        verbose_name = _("Checkin")
        verbose_name_plural = _("Checkins")

    account_name = models.CharField(
        max_length=255,
        verbose_name=_("Account Name"),
        help_text=_('Origin account/holder name.'))
    account_number = models.CharField(
        max_length=255,
        verbose_name=_("Account Number"),
        help_text=_('Origin account number.'))
    provider_name = models.CharField(
        max_length=255,
        verbose_name=_("Provider name"),
        help_text=_('Origin provider. (Bank Mandiri or Gopay)'))
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        limit_choices_to={'model__in': ['donation']},
        verbose_name=_('reference type'),
        blank=True, null=True,
    )
    object_id = models.CharField(_('reference id'), max_length=100, blank=True, null=True)

    def get_amount(self):
        return self.amount

    def __str__(self):
        return "{} / {}".format(self.inner_id, self.account_name)

    def save(self, *args, **kwargs):
        self.flow = 'IN'
        super().save(*args, kwargs)


class PayableModel(models.Model):
    class Meta:
        abstract = True

    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Paid at"))
    is_paid = models.BooleanField(default=False, verbose_name=_("Paid at"))

    def make_paid(self):
        self.paid_at = timezone.now()
        self.is_paid = True
        self.save()
