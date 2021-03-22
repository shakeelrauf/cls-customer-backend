from django.contrib import admin
from django.contrib.auth.models import Group
from django.conf import settings
from rest_framework.authtoken.models import TokenProxy
from .models import User, UserProfile, UserAccess, Audit, AccountNumber, FileNumber, Transaction


# Register your models here.
class UserAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'last_login', 'last_modified', 'created_at',
                    'is_superuser', 'is_staff', 'is_active', 'user_type', 'parent', 'braintree_customer_id',
                    'get_account_number', 'get_primary_user']

    list_filter = ('userprofile__account_number__account_number', 'user_type')

    search_fields = ('email', 'phone', 'first_name', 'last_name', 'userprofile__account_number__account_number')

    ordering = ('first_name', 'last_name')

    def get_account_number(self, obj):
        return obj.userprofile.account_number

    def get_primary_user(self, obj):
        return UserProfile.objects.get(user__user_type='primary', account_number=obj.userprofile.account_number).user


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_user', 'get_parent_user', 'account_number', 'get_file_numbers']

    search_fields = ('account_number__account_number', 'user__email', 'file_numbers__file_number')

    ordering = ('user__first_name', 'user__last_name')

    def get_file_numbers(self, obj):
        return ', '.join([file.file_number for file in obj.file_numbers.all()])

    def get_user(self, obj):
        return obj.user.full_name()

    def get_parent_user(self, obj):
        if obj.user.parent:
            return obj.user.parent.full_name()


class UserAccessAdmin(admin.ModelAdmin):
    list_display = ['user', 'key_finder', 'door_finder', 'inv_statements', 'quotes', 'hs_signatory', 'add_user',
                    'key_ring', 'service_request', 'audit', 'get_account_number', 'get_parent_user', 'get_primary_user']

    search_fields = ('user__userprofile__account_number__account_number',
                     'user__userprofile__file_numbers__file_number')

    ordering = ('user__email',)

    def get_account_number(self, obj):
        return obj.user.userprofile.account_number

    def get_primary_user(self, obj):
        return UserProfile.objects.get(
            user__user_type='primary', account_number=obj.user.userprofile.account_number
        ).user

    def get_parent_user(self, obj):
        if obj.user.parent:
            return obj.user.parent


class AccountNumberAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'exp_date', 'is_registered']

    search_fields = ('account_number',)

    list_filter = ('is_registered',)

    ordering = ('account_number',)


class FileNumberAdmin(admin.ModelAdmin):
    list_display = ['account', 'file_number', 'location', 'system_name']

    search_fields = ('account__account_number', 'file_number', 'location', 'system_name')

    ordering = ('account',)


class AuditAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'modifications', 'get_parent_user', 'get_primary_user']

    search_fields = ('user__email', 'date', 'user__parent__email')

    ordering = ('-date',)

    def get_parent_user(self, obj):
        if obj.user.parent:
            return obj.user.parent

    def get_primary_user(self, obj):
        return UserProfile.objects.get(
            user__user_type='primary', account_number=obj.user.userprofile.account_number
        ).user


class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'user', 'timestamp', 'status', 'amount', 'invoice', 'pay_for', 'bt_status']

    search_fields = ('user__email', 'transaction', 'timestamp', 'status', 'amount', 'invoice', 'pay_for', 'bt_status')

    list_filter = ('pay_for', 'bt_status')

    ordering = ('-timestamp',)


# register with admin app
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserAccess, UserAccessAdmin)
admin.site.register(AccountNumber, AccountNumberAdmin)
admin.site.register(FileNumber, FileNumberAdmin)
admin.site.register(Audit, AuditAdmin)
admin.site.register(Transaction, TransactionAdmin)

admin.site.site_header = "Calgary Lock and Safe Admin"
admin.site.site_title = "Calgary Lock and Safe Admin Portal"
admin.site.index_title = "Welcome to Calgary Lock and Safe Admin Portal"
admin.site.unregister(Group)
admin.site.unregister(TokenProxy)
admin.site.site_url = settings.DOMAIN_NAME
