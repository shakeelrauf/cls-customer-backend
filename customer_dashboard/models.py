from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings


class AccountNumber(models.Model):
    account_number = models.CharField(max_length=255, unique=True)
    exp_date = models.DateField(null=True, blank=True)
    is_registered = models.BooleanField(default=False)

    class Meta:
        db_table = 'AccountNumbers'

    def __str__(self):
        return self.account_number


class FileNumber(models.Model):
    account = models.ForeignKey(AccountNumber, related_name='file_numbers', on_delete=models.CASCADE)
    file_number = models.CharField(max_length=255)  #, unique=True)
    location = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'FileNumbers'

    def __str__(self):
        return self.file_number


# Custom UserManager
class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):  # PermissionsMixin):
    first_name = models.CharField(max_length=255)  # , null=True, blank=True)
    last_name = models.CharField(max_length=255)  # , null=True, blank=True)
    email = models.CharField(max_length=255, unique=True, blank=True)
    password = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255)  # , null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_modified = models.DateTimeField(null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user_type = models.CharField(max_length=255)
    parent = models.ForeignKey('self', related_name='children', blank=True, null=True, on_delete=models.CASCADE)
    braintree_customer_id = models.CharField(max_length=255, null=True, blank=True)
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'User'

    def get_full_name(self):
        # The user is identified by their email address
        return f'{self.first_name} {self.last_name}'

    def get_short_name(self):
        # The user is identified by their email address
        return f'{self.first_name}'

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    def full_name(self):
        return f'{self.first_name if self.first_name else ""} {self.last_name if self.last_name else ""}'


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account_number = models.ForeignKey(AccountNumber, on_delete=models.CASCADE, related_name='users')
    file_numbers = models.ManyToManyField(FileNumber, related_name='usrs')

    class Meta:
        db_table = 'UserProfile'

    def __str__(self):
        return f"{self.account_number.account_number} - {self.user.full_name()}"


# permissions for users
class UserAccess(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key_finder = models.BooleanField(default=True)
    door_finder = models.BooleanField(default=True)
    # Pay Bills
    inv_statements = models.BooleanField(default=True)
    # Accept Quotes
    quotes = models.BooleanField(default=True)
    hs_signatory = models.BooleanField(default=True)
    add_user = models.BooleanField(default=True)
    key_ring = models.BooleanField(default=True)
    service_request = models.BooleanField(default=True)
    audit = models.BooleanField(default=True)

    class Meta:
        db_table = 'UserAccess'

    def __str__(self):
        if self.user.first_name and self.user.last_name:
            return self.user.get_username()
        else:
            return self.user.email


class Audit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audits')
    date = models.DateTimeField(auto_now_add=True)
    modifications = models.CharField(max_length=255)

    class Meta:
        db_table = 'Audit'

    def __str__(self):
        return self.user.get_username()


class Transaction(models.Model):
    transaction = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255)  # success, failed and pending
    amount = models.FloatField()
    invoice = models.CharField(max_length=255)
    pay_for = models.CharField(max_length=255)  # invoice, quote
    bt_status = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'Transaction'

    def __str__(self):
        return self.transaction
