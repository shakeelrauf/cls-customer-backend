from django.conf import settings
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.conf.global_settings import EMAIL_HOST_USER
from django.template.loader import render_to_string

from rest_framework import status
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from email.mime.image import MIMEImage
from faker import Faker
import datetime
import re
import itertools

from customer_dashboard.models import User, UserProfile, UserAccess, Audit, AccountNumber, FileNumber
from customer_dashboard.custom_exception import EmailNotMatchedException, PasswordException, NotFoundError, \
    OldPasswordNotMatched
from customer_dashboard.query import get_last_name

faker = Faker()

# regular exp pattern for password
# minimum 8 char with one upper, one lower, one special char and one numeric value is must
PASSWORD_PATTERN = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
LOGO_PATH = '/images/logo.png'


# serializer for user model
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }


# serializer for creating new primary user (if account number is already exist in database)
class CreateNewPrimaryUserSerializer(serializers.ModelSerializer):
    confirm_email = serializers.CharField(required=False)
    account_number = serializers.CharField(source='userprofile.account_number', required=False)

    def validate_password(self, value):
        if re.match(PASSWORD_PATTERN, value):
            return value
        else:
            raise PasswordException

    def validate(self, attrs):
        if attrs.get('email') != attrs.get('confirm_email') or attrs.get('email') == '' or attrs.get('confirm_email') == '':
            raise EmailNotMatchedException
        return attrs

    def create(self, validated_data):
        profile_data = validated_data.pop('userprofile')
        account_obj = AccountNumber.objects.get(account_number=profile_data['account_number'])
        with transaction.atomic():
            # if account number is exist and user is not registered, then only create new primary user
            password = validated_data.pop('password')
            validated_data.pop('confirm_email')
            validated_data['user_type'] = 'primary'
            user = super().create(validated_data)
            user.set_password(password)
            user.save()
            if user:
                # create user access object
                UserAccess.objects.create(user=user)
                # add exp date and registered info in account number table
                account_obj.exp_date = datetime.date.today() + datetime.timedelta(days=30)
                account_obj.is_registered = True
                account_obj.save()
                # create user profile object
                user_profile = UserProfile.objects.create(user=user, account_number=account_obj)
                # add file number of primary users in userprofile_filenumber table (many to many field)
                file_numbers = account_obj.file_numbers.all()
                user_profile.file_numbers.add(*file_numbers)
        return user

    class Meta:
        model = User
        fields = ['email', 'confirm_email', 'password', 'first_name', 'last_name', 'phone', 'account_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'confirm_email': {'write_only': True}
        }


# serializer of changing password for new additional user
class ChangePasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField()

    def validate_password(self, value):
        if re.match(PASSWORD_PATTERN, value):
            return value
        raise ValueError(
            'Password should be minimum 8 characters with one upper and one lower case and one numeric value')

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('old_password'):
            return attrs
        raise PasswordException

    def update(self, instance, validated_data):
        if instance.check_password(validated_data.get('old_password', None)):
            with transaction.atomic():
                instance.set_password(validated_data.get('password'))
                instance.last_modified = datetime.datetime.now()
                instance.save()
                Audit.objects.create(
                    user=instance,
                    modifications=f"{instance.full_name()} change password"
                )
        else:
            raise OldPasswordNotMatched
        return instance

    class Meta:
        model = User
        fields = ['password', 'old_password']


# serializer of user access model
class UserAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccess
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True}
        }


# serializer for file number model
class FileNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileNumber
        fields = ['id', 'file_number', 'location']


# serializer for adding new additional user (manage user tab)
class AdditionalUserSerializer(serializers.ModelSerializer):
    useraccess = UserAccessSerializer()
    file_numbers = serializers.ListField(write_only=True, source='userprofile.file_numbers')
    method = serializers.CharField(required=False)
    user_list = []

    # get all users list for particular account number
    def get_users(self, parent_user):
        users = parent_user.children.all()
        if users:
            for usr in users:
                AdditionalUserSerializer.user_list.append(usr)
                usrs = usr.children.all()
                if usrs:
                    self.get_users(usr)
        return AdditionalUserSerializer.user_list

    # check first and last name if already exist for particular account number
    def validate(self, attrs):
        if attrs.get('method').lower() == 'post':
            # get primary user
            primary_user = UserProfile.objects.get(
                account_number=self.context['request'].user.userprofile.account_number,
                user__user_type='primary'
            ).user
            users = self.get_users(primary_user)
            users.append(primary_user)
            first_name = attrs.get('first_name')
            last_name = attrs.get('last_name')
            full_name = first_name.strip() + ' ' + last_name.strip()
            for user in users:
                if user.full_name() == full_name:
                    raise ValueError
            return attrs
        else:
            return attrs

    # create additional user
    def create(self, validated_data):
        with transaction.atomic():
            password = faker.password()
            access = dict(validated_data.pop('useraccess'))
            userprofile = validated_data.pop('userprofile')
            files = userprofile.pop('file_numbers')
            validated_data['user_type'] = 'additional'
            validated_data['parent'] = self.context['request'].user
            validated_data.pop('method')
            user = super().create(validated_data)
            user.set_password(password)
            user.save()
            if user:
                # create user profile object
                user_profile_obj = UserProfile.objects.create(
                    user=user,
                    account_number=self.context['request'].user.userprofile.account_number
                )
                # assign file numbers
                user_profile_obj.file_numbers.add(*files)
                # check parent user permissions
                usr_access = {}
                for key, value in access.items():
                    # if parent object have permission
                    if getattr(self.context['request'].user.useraccess, key):
                        usr_access[key] = value
                    # if parent object have no permission
                    else:
                        usr_access[key] = False
                # crete user access object
                UserAccess.objects.create(user=user, **usr_access)
                # create audit object
                Audit.objects.create(
                    user=self.context['request'].user,
                    modifications=f"{self.context['request'].user.full_name()} added {user.full_name()}"
                )
                esc_last_name = get_last_name(self.context['request'].user.userprofile.account_number.account_number)

                # send mail to additional user
                msg_additional = EmailMultiAlternatives(
                    'Calgary Lock and Safe',
                    render_to_string(
                        'email/create_additional_to_additional_user.html',
                        {
                            'full_name': user.full_name(),
                            'primary_full_name': self.context['request'].user.full_name(),
                            'esc_last_name': esc_last_name,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'phone': user.phone,
                            'file_numbers': user.userprofile.file_numbers.all(),
                            'password': password
                        }
                    ),
                    EMAIL_HOST_USER,
                    [validated_data['email']]
                )
                msg_additional.content_subtype = 'html'  # Main content is text/html
                msg_additional.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
                with open(settings.STATIC_DIR + LOGO_PATH, 'rb') as f:
                    file = f.read()
                image = MIMEImage(file)
                image.add_header('Content-ID', '<logo.png>')
                msg_additional.attach(image)
                msg_additional.send()

                # send mail to primary user
                msg = EmailMultiAlternatives(
                    "Calgary Lock and Safe",
                    render_to_string(
                        'email/create_additional_to_primary_user.html',
                        {
                            'full_name': self.context['request'].user.full_name(),
                            'account_number': self.context['request'].user.userprofile.account_number.account_number,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'phone': user.phone,
                            'file_numbers': user.userprofile.file_numbers.all()
                        }
                    ),
                    EMAIL_HOST_USER,
                    [self.context['request'].user.email]
                )
                msg.content_subtype = 'html'
                msg.mixed_subtype = 'related'
                with open(settings.STATIC_DIR + LOGO_PATH, 'rb') as f:
                    file = f.read()
                image = MIMEImage(file)
                image.add_header('Content-ID', '<logo.png>')
                msg.attach(image)
                msg.send()
        return user

    # update additional user
    def update(self, instance, validated_data):
        with transaction.atomic():
            access = validated_data.pop('useraccess')
            instance.first_name = validated_data.get('first_name', instance.first_name)
            instance.last_name = validated_data.get('last_name', instance.last_name)
            instance.phone = validated_data.get('phone', instance.phone)
            instance.last_modified = datetime.datetime.now()
            instance.save()
            # set user permission
            for key, value in access.items():
                # if parent object have permission
                if getattr(self.context['request'].user.useraccess, key):
                    setattr(instance.useraccess, key, access.get(key))
            instance.useraccess.save()
            # create audit object
            Audit.objects.create(
                user=self.context['request'].user,
                modifications=f"{self.context['request'].user.full_name()} update {instance.full_name()}"
            )
            # update file numbers
            userprofile = validated_data.pop('userprofile')
            updated_files = userprofile.pop('file_numbers')
            if len(updated_files) > 0:
                # get old file numbers
                files = [file.id for file in instance.userprofile.file_numbers.all()]
                # remove old file numbers
                instance.userprofile.file_numbers.remove(*files)
                # update new file numbers
                instance.userprofile.file_numbers.add(*updated_files)
        return instance

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone', 'is_active', 'useraccess', 'file_numbers',
                  'method']
        extra_kwargs = {
            'password': {'write_only': True},
            'is_active': {'read_only': True},
            'method': {'write_only': True}
        }

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['file_numbers'] = list(itertools.chain(*instance.userprofile.file_numbers.all().values_list('id')))
        return response


# serializer for activate and deactivate user
class ToogleUserActiveSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        with transaction.atomic():
            if instance.is_active:
                instance.is_active = False
                action = 'deactivate'
            else:
                instance.is_active = True
                action = 'activate'
            instance.last_modified = datetime.datetime.now()
            instance.save()
            # create audit object
            Audit.objects.create(
                user=self.context['request'].user,
                modifications=f"{self.context['request'].user.full_name()} {action} {instance.full_name()}"
            )
        return instance

    class Meta:
        model = User
        fields = ['is_active']
        extra_kwargs = {
            'user_type': {'read_only': True}
        }


# serializer for audit model
class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audit
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['username'] = instance.user.full_name()
        return response


# custom serializer for login user
class CustomLoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        'error': True,
        'status': status.HTTP_401_UNAUTHORIZED,
        'message': 'No active account found with the given credentials'
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        self.get_token(self.user)
        data['is_active'] = UserSerializer(self.user).data['is_active']
        data['user_type'] = UserSerializer(self.user).data['user_type']
        data['last_login'] = UserSerializer(self.user).data['last_login']
        data['last_modified'] = UserSerializer(self.user).data['last_modified']
        data['username'] = self.user.full_name()
        data['user_access'] = UserAccessSerializer(self.user.useraccess).data
        if self.user.is_active:
            self.user.last_login = datetime.datetime.now()
            self.user.save()
        return data


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.CharField()

    def validate_email(self, value):
        if value == '':
            raise NotFoundError
        else:
            return value

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs['email'])
        except User.DoesNotExist:
            raise User.DoesNotExist('User does not exist')
        else:
            if user:
                new_password = faker.password()
                user.set_password(new_password)
                user.save()
                # sending password mail to user
                msg = EmailMultiAlternatives(
                    'Reset password of Calgary Locks and Safe',
                    render_to_string(
                        'email/reset_password.html',
                        {
                            'password': new_password,
                            'first_name': user.first_name,
                            'last_name': user.last_name
                        }
                    ),
                    EMAIL_HOST_USER,
                    [user.email]
                )
                msg.content_subtype = 'html'  # Main content is text/html
                msg.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
                with open(settings.STATIC_DIR + LOGO_PATH, 'rb') as f:
                    file = f.read()
                image = MIMEImage(file)
                image.add_header('Content-ID', '<logo.png>')
                msg.attach(image)
                msg.send()
            else:
                raise ValueError('Usre is not a valid user')
        return attrs
