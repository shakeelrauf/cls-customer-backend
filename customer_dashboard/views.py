from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.views import TokenObtainPairView

from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf.global_settings import EMAIL_HOST_USER
from django.conf import settings
import pdb

import pdfkit
import logging
import datetime
import braintree
from email.mime.image import MIMEImage

from customer_dashboard.braintree import get_gateway
from customer_dashboard.models import User, Audit, AccountNumber, FileNumber, Transaction, UserProfile
from customer_dashboard.serializers import CreateNewPrimaryUserSerializer, ChangePasswordSerializer, \
    AdditionalUserSerializer, UserAccessSerializer, UserSerializer, AuditSerializer, ToogleUserActiveSerializer, \
    FileNumberSerializer, CustomLoginSerializer, ResetPasswordSerializer
from customer_dashboard.query import update_company_details, get_company_details, get_accounting, get_invoice_list, get_invoice, \
    get_quotations,get_dispatch_parts, get_service_request,get_service_request_dispatches, get_quotes, get_quotes_list, get_invoice_for_query, get_last_name, \
    get_all_invoice_of_location, get_all_invoice, get_invoice_list_with_address
from customer_dashboard.custom_exception import EmailNotMatchedException, PasswordException, NotFoundError, \
    ConnectionError, ESCDataNotFetchingError, OldPasswordNotMatched


logger = logging.getLogger(__name__)
INTERNAL_SERVER_ERROR_500_MESSAGE = 'Something went wrong! Please try later'
ESC_DATABASE_CONNECTION_ERROR = 'ESC Database Connection Error'
PAYMENT_APPROVED_EMAIL_SUBJECT = "Payment Approved - Calgary Lock and Safe"
PAYMENT_DENIED_EMAIL_SUBJECT = "Payment Denied - Calgary Lock and Safe"
UPDATE_COMPANY_DETAILS_SUBJECT = "Company Details Updated - Calgary Lock and Safe"
PAYMENT_APPROVED_TEMPLATE = 'email/payment_approved_to_customer.html'
PAYMENT_APPROVED_TO_CALGARY_TEMPLATE = 'email/payment_approved_to_calgary.html'
PAYMENT_DENIED_TO_CUSTOMER_TEMPLATE = 'email/payment_denied_to_customer.html'
UPDATE_COMPANY_DETAILS_TEMPLATE = 'email/update_company_details.html'
PAYMENT_DENIED_TO_CALGARY_TEMPLATE = 'email/payment_denied_to_calgary.html'
PAYMENT_SUCCESSFUL_MESSAGE = 'Payment successful'
PAYMENT_DENIED_MESSAGE = 'Payment denied'
LOGO_PATH = '/images/logo.png'


# create new primary user
class CreateNewPrimaryUserView(APIView):
    def get_account_obj(self, account_number):
        try:
            return AccountNumber.objects.get(account_number=account_number)
        except AccountNumber.DoesNotExist:
            return None

    def post(self, request):
        try:
            account_obj = self.get_account_obj(request.data['account_number'])
            # check account number is already exist in database or not
            if account_obj and not account_obj.is_registered:
                serializer = CreateNewPrimaryUserSerializer(data=request.data, context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    response = {'success': True, 'status': status.HTTP_200_OK, 'data': serializer.data,
                                'message': 'User created successfully'}
                    # send mail to customer
                    subject = f"Calgary Lock and Safe"
#
                    msg = EmailMultiAlternatives(
                        subject,
                        render_to_string(
                            'email/create_primary_to_customer.html',
                            {
                                'account_number': request.data['account_number'],
                                'first_name': request.data['first_name'],
                                'last_name': request.data['last_name'],
                                'phone': request.data['phone']
                            }
                        ),
                        EMAIL_HOST_USER,
                        [request.data['email']]
                    )
                    msg.content_subtype = 'html'  # Main content is text/html
                    msg.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
                    with open(settings.STATIC_DIR + LOGO_PATH, 'rb') as f:
                        file = f.read()
                    image = MIMEImage(file)
                    image.add_header('Content-ID', '<logo.png>')
                    msg.attach(image)
                    # msg.send()

                    # send mail to calgary
                    subject = f"{request.data['account_number']} - {request.data['first_name']} {request.data['last_name']}"
#
                    msg = EmailMultiAlternatives(
                        subject,
                        render_to_string(
                            'email/create_primary_to_calgary.html',
                            {
                                'account_number': request.data['account_number'],
                                'first_name': request.data['first_name'],
                                'last_name': request.data['last_name'],
                                'phone': request.data['phone']
                            }
                        ),
                        EMAIL_HOST_USER,
                        [settings.EMAIL_FOR_CREATE_NEW_PRIMARY_USER]
                    )
                    msg.content_subtype = 'html'  # Main content is text/html
                    msg.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
                    with open(settings.STATIC_DIR + LOGO_PATH, 'rb') as f:
                        file = f.read()
                    image = MIMEImage(file)
                    image.add_header('Content-ID', '<logo.png>')
                    msg.attach(image)
                    msg.send()
            # if account number is already exist and user already registered
            elif account_obj and account_obj.is_registered:
                response = {'error': True, 'status': status.HTTP_400_BAD_REQUEST, 'message': 'User already registered'}
            # if account number does not exist in account number table
            else:
                response = {'error': True, 'status': status.HTTP_404_NOT_FOUND,
                            'message': 'Account Number does not exist'}
        except PasswordException:
            response = {'error': True, 'status': status.HTTP_406_NOT_ACCEPTABLE,
                        'message': 'Password should be minimum 8 characters with one upper and one lower '
                                   'case, one numeric value and one special character'}
        except EmailNotMatchedException:
            response = {'error': True, 'status': status.HTTP_409_CONFLICT,
                        'message': 'Both email and confirm email should be matched!'}
        except Exception as e:
            print(e)
            if 'email' in str(e.args):
                response = {'error': True, 'status': status.HTTP_401_UNAUTHORIZED,
                            'message': 'User with this email ID already exist'}
            else:
                logger.error('%s', e)
                response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                            'message': INTERNAL_SERVER_ERROR_500_MESSAGE}
        return Response(response)


# additional user
class AdditionalUserView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    user_list = []

    def get_instance(self, request, pk):
        try:
            instance = User.objects.get(id=pk)
            if instance.userprofile.account_number == request.user.userprofile.account_number:
                return instance
        except User.DoesNotExist:
            return None

    # get all user list of current user account number
    def get_users(self, parent_user):
        users = parent_user.children.all()
        if users:
            for usr in users:
                AdditionalUserView.user_list.append(usr)
                usrs = usr.children.all()
                if usrs:
                    self.get_users(usr)
        return AdditionalUserView.user_list

    # list of all additional users (of current user)
    def get(self, request):
        primary_user = UserProfile.objects.get(
            account_number=request.user.userprofile.account_number,
            user__user_type='primary'
        ).user
        additional_users = self.get_users(primary_user)
        # remove current user from users list
        if request.user in additional_users:
            additional_users.remove(request.user)
        # sort users list according to first_name
        additional_users.sort(key=lambda x: x.full_name().lower())

        results = self.paginate_queryset(additional_users, request, view=self)
        serializer = AdditionalUserSerializer(results, many=True)

        user_access_serializer = UserAccessSerializer(request.user.useraccess)
        user_serializer = UserSerializer(request.user).data
        user_info = {
            'first_name': user_serializer['first_name'],
            'last_name': user_serializer['last_name'],
            'last_login': user_serializer['last_login'],
            'last_modified': user_serializer['last_modified']
        }
        response = {
            'current_user': user_info,
            'file_numbers': FileNumberSerializer(request.user.userprofile.file_numbers.all(), many=True).data,
            'current_user_access': user_access_serializer.data,
            'data': serializer.data
        }
        AdditionalUserView.user_list = []
        return self.get_paginated_response(response)

    # for create new additional user
    def post(self, request):
        if request.user.user_type == 'primary' or request.user.useraccess.add_user:
            try:
                serializer = AdditionalUserSerializer(data=request.data, context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    response = {'success': True, 'status': status.HTTP_200_OK, 'data': serializer.data,
                                'message': 'User added successfully'}
            except ValueError:
                response = {'error': True, 'status': status.HTTP_409_CONFLICT,
                            'message': 'User with this user name already exist'}
            except Exception as e:
                print(e)
                if 'email' in str(e.args):
                    response = {'error': True, 'status': status.HTTP_401_UNAUTHORIZED,
                                'message': 'User with this email ID already exist'}
                else:
                    logger.error('%s', e)
                    response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                                'message': INTERNAL_SERVER_ERROR_500_MESSAGE}
        else:
            response = {'error': True, 'status': status.HTTP_400_BAD_REQUEST,
                        'message': 'User have no permission to add new user'}
        return Response(response)

    # for edit user access, file numbers and user information
    def put(self, request, pk):
        if request.user.useraccess.add_user:
            try:
                serializer = AdditionalUserSerializer(
                    self.get_instance(request, pk), data=request.data, context={'request': request}
                )
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    response = {'success': True, 'status': status.HTTP_200_OK,
                                'message': 'User info updated successfully'}
            except Exception as e:
                print(e)
                logger.error('%s', e)
                response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                            'message': INTERNAL_SERVER_ERROR_500_MESSAGE}
            return Response(response)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_401_UNAUTHORIZED,
                'message': 'You have no permission to update user detail'
            })

    # for activate and deactivate users
    def patch(self, request, pk):
        if request.user.useraccess.add_user:
            try:
                serializer = ToogleUserActiveSerializer(
                    self.get_instance(request, pk), data=request.data, context={'request': request}
                )
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    response = {'success': True, 'status': status.HTTP_200_OK, 'data': serializer.data,
                                'message': f"User {'activate' if request.user.is_active else 'deactivate'} successfully"}
            except Exception as e:
                print(e)
                logger.error('%s', e)
                response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                            'message': INTERNAL_SERVER_ERROR_500_MESSAGE}
        else:
            response = {'error': True, 'status': status.HTTP_400_BAD_REQUEST,
                        'message': 'You have no permission to activate/deactivate this user or user does not exist'}
        return Response(response)


# change password
class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    # for changing current password
    def patch(self, request):
        try:
            serializer = ChangePasswordSerializer(
                request.user, data=request.data, partial=True
            )
            if serializer.is_valid(raise_exception=False):
                serializer.save()
                response = {'success': True, 'status': status.HTTP_200_OK,
                            'message': 'Password changed successfully'}
        except ValueError:
            response = {'error': True, 'status': status.HTTP_406_NOT_ACCEPTABLE,
                        'message': 'Password should be minimum 8 characters with one upper and one '
                                   'lower case, one numeric value and one special character'}
        except PasswordException:
            response = {'error': True, 'status': status.HTTP_400_BAD_REQUEST,
                        'message': 'New password should not be the same as old password'}
        except OldPasswordNotMatched:
            response = {'error': True, 'status': status.HTTP_401_UNAUTHORIZED,
                        'message': 'Old Password not matched'}
        except Exception as e:
            logger.error('%s', e)
            response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                        'message': INTERNAL_SERVER_ERROR_500_MESSAGE}
        return Response(response)


# audit
class AuditView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    user_list = []

    # get all user list of current user account number
    def get_users(self, parent_user):
        users = parent_user.children.all()
        if users:
            for usr in users:
                AuditView.user_list.append(usr)
                usrs = usr.children.all()
                if usrs:
                    self.get_users(usr)
        return AuditView.user_list

    def get(self, request):
        if request.user.useraccess.audit:
            # get primary user
            primary_user = UserProfile.objects.get(
                account_number=request.user.userprofile.account_number,
                user__user_type='primary'
            ).user

            # list of all users
            all_users = self.get_users(primary_user)

            # add primary user in users list
            all_users.append(primary_user)

            params = request.query_params

            # get start_date and end_date
            if 'start_date' in params.keys() and 'end_date' in params.keys() and params.get('start_date') != '' \
                    and params.get('end_date') != '':
                start_date = datetime.datetime.strptime(params.get('start_date'), '%Y-%m-%d')
                end_date = datetime.datetime.strptime(params.get('end_date'), '%Y-%m-%d') + datetime.timedelta(days=1)
            else:
                start_date = None
                end_date = None

            # get first and last name
            if 'first_name' in params.keys() and 'last_name' in params.keys() and params.get('first_name') != '' \
                    and params.get('last_name') != '':
                first_name = params.get('first_name', None)
                last_name = params.get('last_name', None)
            else:
                first_name = None
                last_name = None

            # if params.get('first_name') != 'null' and params.get('last_name') != 'null':
            if first_name and last_name:
                # match first name and last name with users of current user's account number
                try:
                    u = UserProfile.objects.get(
                        account_number=request.user.userprofile.account_number,
                        user__first_name=params.get('first_name'),
                        user__last_name=params.get('last_name')
                    ).user
                    user = u

                except UserProfile.DoesNotExist:
                    return Response({
                        'error': True,
                        'status': status.HTTP_400_BAD_REQUEST,
                        'message': 'User does not exist'
                    })

            # first and last name with date range
            if first_name and last_name and start_date and end_date:
                instance = Audit.objects.filter(user=user, date__range=(start_date, end_date)).order_by('-date')

            # all users with date range
            elif not first_name and not last_name and start_date and end_date:
                instance = Audit.objects.filter(user__in=all_users, date__range=(start_date, end_date)).order_by(
                    '-date')

            # first and last name without date range
            elif first_name and last_name and not start_date and not end_date:
                instance = Audit.objects.filter(user=user).order_by('-date')

            # all users without any filter
            else:
                instance = Audit.objects.filter(user__in=all_users).order_by('-date')
            results = self.paginate_queryset(instance, request, view=self)
            serializer = AuditSerializer(results, many=True)
            AuditView.user_list = []
            return self.get_paginated_response(serializer.data)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'You have no permission to view audit trail'
            })


# list current user file numbers
class FileNumbersView(APIView):
    permission_classes = (IsAuthenticated,)

    # list of all file numbers which is assigned to user
    def get(self, request):
        cus_no = request.user.userprofile.account_number.account_number
        file_numbers = request.user.userprofile.file_numbers.all()
        serializer = FileNumberSerializer(file_numbers, many=True)
        try:
            last_name = get_last_name(cus_no)
            response = {
                'cus_no': cus_no,
                'last_name': last_name,
                'data': serializer.data
            }
        except NotFoundError:
            response = {
                'error': True,
                'status': status.HTTP_404_NOT_FOUND,
                'message': 'Customer number Not Found'
            }
        return Response(response)

    # naming file numbers by primary user only
    def patch(self, request, pk):
        if request.user.user_type == 'primary':
            try:
                serializer = FileNumberSerializer(
                    FileNumber.objects.get(id=pk),
                    data=request.data,
                    partial=True
                )
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    response = {
                        'success': True,
                        'status': status.HTTP_200_OK,
                        'data': serializer.data,
                        'message': "File Number updated successfully"
                    }
            except FileNumber.DoesNotExist:
                response = {
                    'error': True,
                    'status': status.HTTP_404_NOT_FOUND,
                    'message': 'File Number does not exist'
                }
            except Exception as e:
                print(e)
                response = {
                    'error': True,
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': INTERNAL_SERVER_ERROR_500_MESSAGE
                }
            return Response(response)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_401_UNAUTHORIZED,
                'message': "You have no right to update file number's info"
            })


# custom login view
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomLoginSerializer


# request for reset password
class ResetPasswordView(APIView):
    permission_classes = (AllowAny,)

    # sending new auto generated password to user's email
    def post(self, request):
        if request.data.get('email') != '':
            try:
                serializer = ResetPasswordSerializer(data=request.data, context={'request': request})
                serializer.is_valid(raise_exception=False)
                response = {'success': True, 'status': status.HTTP_200_OK,
                            'message': 'Password reset successfully, please check your registered email inbox'}
            except ValueError:
                response = {'error': True, 'status': status.HTTP_401_UNAUTHORIZED,
                            'message': 'User is not a valid user'}
            except NotFoundError:
                response = {'error': True, 'status': status.HTTP_400_BAD_REQUEST,
                            'message': 'Email should not be blank or not a valid email'}
            except User.DoesNotExist:
                response = {'error': True, 'status': status.HTTP_404_NOT_FOUND, 'message': 'User does not exist'}
            except Exception as e:
                print(e)
                logger.error('%s', e)
                response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                            'message': INTERNAL_SERVER_ERROR_500_MESSAGE}
            return Response(response)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'Email should not be blank or not a valid email'
            })


# ---------------------------------------------- CLSESC DATABASE ----------------------------------------------------
# ---------------------------------------------- COMPANY DETAILS ----------------------------------------------------
# Company Details View
class CompanyDetailsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_company_details(cus_no)
            return JsonResponse(data, safe=False)
        except NotFoundError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_404_NOT_FOUND,
                'message': f'No record found for {cus_no} Account Number/Customer Number'
            })
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })

    def post(self, request, custNo, locNo):
        res = update_company_details(custNo, locNo, request.data)
        if res:
            send_mail(
                    UPDATE_COMPANY_DETAILS_SUBJECT,
                    f"Update Company with CustNo {custNo} and Location {locNo} by {request.user.full_name()}",
                    EMAIL_HOST_USER,
                    [request.user.email, settings.EMAIL_TO_CALGARY_REPORTS],
                    html_message=render_to_string(
                        UPDATE_COMPANY_DETAILS_TEMPLATE,
                        {
                            'custNo' : custNo,
                            'locNo': locNo,
                            'user': request.user.full_name(),
                            'locName': res[0],
                            'address': res[1]
                        }
                    )
                )
            return JsonResponse({"success": True},  safe=False)
        else:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })

# --------------------------------------------------- ACCOUNTING ----------------------------------------------------
# Accounting View
class AccountingView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if request.user.useraccess.inv_statements:
            try:
                cus_no = request.user.userprofile.account_number.account_number
                data = get_accounting(cus_no)
                return JsonResponse(data, safe=False)
            except NotFoundError:
                return JsonResponse({
                    'error': True,
                    'status': status.HTTP_404_NOT_FOUND,
                    'message': f'No record found for {cus_no} Account Number/Customer Number'
                })
            except ConnectionError:
                logger.error(ESC_DATABASE_CONNECTION_ERROR)
                return JsonResponse({
                    'error': True,
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': INTERNAL_SERVER_ERROR_500_MESSAGE
                })
            except ESCDataNotFetchingError:
                return JsonResponse({
                    'error': True,
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': INTERNAL_SERVER_ERROR_500_MESSAGE
                })
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'You have no permission for pay bills'
            })


# List of Invoices
class ListInvoiceView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, loc_no):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_invoice_list(cus_no, loc_no)
            return JsonResponse(data, safe=False)
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })


# Show Invoice
class InvoiceView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, loc_no, invoice):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_invoice(cus_no, loc_no, invoice)
            return JsonResponse(data, safe=False)
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })


# Send mail to calgary for any query related to invoice
class CustomerHelpAccountingView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        cus_no = request.user.userprofile.account_number.account_number
        subject = f"{cus_no} have some query related to invoice"
        try:
            # mail send to calgary
            msg = EmailMultiAlternatives(
                subject,
                render_to_string(
                    'email/customer_help_to_calgary.html',
                    {
                        'cus_no': cus_no,
                        'location': request.data['location'],
                        'address': request.data['address'],
                        'amount': request.data['amount'],
                        'invoices': get_invoice_for_query(cus_no, request.data['loc_no']),
                        'query': request.data['message']
                    }
                ),
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY]
            )
            msg.content_subtype = 'html'  # Main content is text/html
            msg.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
            with open(settings.STATIC_DIR + LOGO_PATH, 'rb') as f:
                file = f.read()
            image = MIMEImage(file)
            image.add_header('Content-ID', '<logo.png>')
            msg.attach(image)
            msg.send()

            response = {
                'success': True,
                'status': status.HTTP_200_OK,
                'message': 'Query send successfully'
            }
        except Exception as e:
            print(e)
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            response = {
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': 'Something went wrong, please contact to Calgary Lock and Safe'
            }
        return Response(response)


# Get token for payment
class GetTokenForPaymentView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if settings.BRAINTREE_PRODUCTION:
            braintree_env = braintree.Environment.Production
        else:
            braintree_env = braintree.Environment.Sandbox
        # configure Braintree
        braintree.Configuration.configure(
            braintree_env,
            merchant_id=settings.BRAINTREE_MERCHANT_ID,
            public_key=settings.BRAINTREE_PUBLIC_KEY,
            private_key=settings.BRAINTREE_PRIVATE_KEY
        )
        if not request.user.braintree_customer_id:
            result = braintree.Customer.create({
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'phone': request.user.phone
            })
            if result.is_success:
                request.user.braintree_customer_id = result.customer.id
                request.user.save()
        braintree_client_token = braintree.ClientToken.generate({
            'customer_id': request.user.braintree_customer_id
        })
        return Response({'token': braintree_client_token})


# Pay individual invoice
class PayInvoiceView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if settings.BRAINTREE_PRODUCTION:
            braintree_env = braintree.Environment.Production
        else:
            braintree_env = braintree.Environment.Sandbox
        # configure Braintree
        braintree.Configuration.configure(
            braintree_env,
            merchant_id=settings.BRAINTREE_MERCHANT_ID,
            public_key=settings.BRAINTREE_PUBLIC_KEY,
            private_key=settings.BRAINTREE_PRIVATE_KEY
        )
        payment_method_nonce = request.data['payment_method_nonce']
        result = braintree.Transaction.sale({
            'amount': str(request.data['amount']),
            'payment_method_nonce': payment_method_nonce,
            'options': {
                'submit_for_settlement': True
            }
        })
        transaction_id = result.transaction.id
        account_number = request.user.userprofile.account_number.account_number
        gateway = get_gateway()
        card_details = gateway.transaction.find(transaction_id).credit_card_details.last_4
        if result.is_success:
            # update database
            transaction = Transaction.objects.create(
                transaction=transaction_id,
                user=request.user,
                status='success',
                amount=request.data['amount'],
                invoice=request.data['invoice'],
                pay_for='invoice',
                bt_status='submitted_for_settlement'
            )
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for invoice of {transaction.invoice} paid by {request.user.full_name()} is approved"
            )
            # send confirmation mail to customer
            send_mail(
                PAYMENT_APPROVED_EMAIL_SUBJECT,
                f"Payment of {request.data['invoice']} approved",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TEMPLATE,
                    {
                        'transaction_id': transaction.id,
                        'customer_id': transaction.user.braintree_customer_id,
                        'invoice': transaction.invoice,
                        'amount': transaction.amount,
                        'date': transaction.timestamp,
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': False
                    }
                )
            )

            # send confirmation mail to calgary
            send_mail(
                f"Payment Approved - {account_number}",
                f"Payment for {request.data['invoice']} of {account_number} approved",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TO_CALGARY_TEMPLATE,
                    {
                        'transaction_id': transaction.id,
                        'customer_id': transaction.user.braintree_customer_id,
                        'invoice': transaction.invoice,
                        'amount': transaction.amount,
                        'date': transaction.timestamp,
                        'account_number': account_number,
                        'multiple': False
                    }
                )
            )
            response = {
                'success': True,
                'status': status.HTTP_202_ACCEPTED,
                'message': PAYMENT_SUCCESSFUL_MESSAGE
            }
        else:
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for invoice of {request.data['invoice']} paid by {request.user.full_name()} is denied"
            )
            # send denied mail to customer
            send_mail(
                PAYMENT_DENIED_EMAIL_SUBJECT,
                f"Payment of {request.data['invoice']} denied",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CUSTOMER_TEMPLATE,
                    {
                        'invoice': request.data['invoice'],
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': False
                    }
                )
            )

            # send denied mail to calgary
            send_mail(
                f"Payment Denied - {account_number}",
                f"Payment for {request.data['invoice']} of {account_number} denied",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CALGARY_TEMPLATE,
                    {
                        'invoice': request.data['invoice'],
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': False
                    }
                )
            )
            response = {
                'error': True,
                'status': status.HTTP_406_NOT_ACCEPTABLE,
                'message':PAYMENT_DENIED_MESSAGE
            }
        return Response(response)


# Pay invoice on location basis
class PayInvoiceForLocationView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, loc_no):
        cus_no = request.user.userprofile.account_number.account_number
        data = get_all_invoice_of_location(cus_no, loc_no)
        return JsonResponse(data, safe=False)

    def post(self, request, loc_no):
        if settings.BRAINTREE_PRODUCTION:
            braintree_env = braintree.Environment.Production
        else:
            braintree_env = braintree.Environment.Sandbox
        # configure Braintree
        braintree.Configuration.configure(
            braintree_env,
            merchant_id=settings.BRAINTREE_MERCHANT_ID,
            public_key=settings.BRAINTREE_PUBLIC_KEY,
            private_key=settings.BRAINTREE_PRIVATE_KEY
        )
        payment_method_nonce = request.data['payment_method_nonce']
        result = braintree.Transaction.sale({
            'amount': str(request.data['amount']),
            'payment_method_nonce': payment_method_nonce,
            'options': {
                'submit_for_settlement': True
            }
        })
        transaction_id = result.transaction.id
        account_number = request.user.userprofile.account_number.account_number
        gateway = get_gateway()
        card_details = gateway.transaction.find(transaction_id).credit_card_details.last_4
        location = request.data['address']
        if result.is_success:
            # update database
            transactions = []
            for invoice_dict in request.data['list_of_invoice']:
                transactions.append(
                    Transaction(
                        transaction=transaction_id,
                        user=request.user,
                        status='success',
                        amount=invoice_dict['amount'],
                        invoice=invoice_dict['invoice'],
                        pay_for='invoice',
                        bt_status='submitted_for_settlement'
                    )
                )
            Transaction.objects.bulk_create(transactions)
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for location '{location}' for all invoice ({', '.join([invoice_dict['invoice'] for invoice_dict in request.data['list_of_invoice']])}) paid by {request.user.full_name()} approved"
            )
            # send confirmation mail to customer
            send_mail(
                PAYMENT_APPROVED_EMAIL_SUBJECT,
                f"Payment of {request.data['location']} for {request.data['address']} approved",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TEMPLATE,
                    {
                        'transaction_id': transaction_id,
                        'customer_id': request.user.braintree_customer_id,
                        'invoice': Transaction.objects.filter(transaction=transaction_id),
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            # send confirmation mail to calgary
            send_mail(
                f"Payment Approved - {account_number}",
                f"Payment of {account_number} approved",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TO_CALGARY_TEMPLATE,
                    {
                        'transaction_id': transaction_id,
                        'customer_id': request.user.braintree_customer_id,
                        'invoice': Transaction.objects.filter(transaction=transaction_id),
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            response = {
                'success': True,
                'status': status.HTTP_202_ACCEPTED,
                'message': PAYMENT_SUCCESSFUL_MESSAGE
            }
        else:
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for location '{location}' for all invoice ({', '.join([invoice_dict['invoice'] for invoice_dict in request.data['list_of_invoice']])}) paid by {request.user.full_name()} denied"
            )
            list_of_invoice = []
            for invoice in request.data['invoice']:
                list_of_invoice.append(invoice['invoice'])
            invoices = ', '.join(list_of_invoice)
            # send denied mail to customer
            send_mail(
                PAYMENT_DENIED_EMAIL_SUBJECT,
                f"Payment of {request.data['location']} for {request.data['address']} denied",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CUSTOMER_TEMPLATE,
                    {
                        'invoice': invoices,
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            # send denied mail to calgary
            send_mail(
                f"Payment Denied - {account_number}",
                f"Payment of {account_number} denied",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CALGARY_TEMPLATE,
                    {
                        'invoice': invoices,
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            response = {
                'error': True,
                'status': status.HTTP_406_NOT_ACCEPTABLE,
                'message': PAYMENT_DENIED_MESSAGE
            }
        return Response(response)


# Pay all invoice
class PayAllInvoiceView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        cus_no = request.user.userprofile.account_number.account_number
        data = get_all_invoice(cus_no)
        return JsonResponse(data, safe=False)

    def post(self, request):
        if settings.BRAINTREE_PRODUCTION:
            braintree_env = braintree.Environment.Production
        else:
            braintree_env = braintree.Environment.Sandbox
        # configure Braintree
        braintree.Configuration.configure(
            braintree_env,
            merchant_id=settings.BRAINTREE_MERCHANT_ID,
            public_key=settings.BRAINTREE_PUBLIC_KEY,
            private_key=settings.BRAINTREE_PRIVATE_KEY
        )
        payment_method_nonce = request.data['payment_method_nonce']
        result = braintree.Transaction.sale({
            'amount': str(request.data['amount']),
            'payment_method_nonce': payment_method_nonce,
            'options': {
                'submit_for_settlement': True
            }
        })
        transaction_id = result.transaction.id
        account_number = request.user.userprofile.account_number.account_number
        gateway = get_gateway()
        card_details = gateway.transaction.find(transaction_id).credit_card_details.last_4
        if result.is_success:
            # update database
            transactions = []
            for invoice_dict in request.data['list_of_invoice']:
                transactions.append(
                    Transaction(
                        transaction=transaction_id,
                        user=request.user,
                        status='success',
                        amount=invoice_dict['amount'],
                        invoice=invoice_dict['invoice'],
                        pay_for='invoice',
                        bt_status='submitted_for_settlement'
                    )
                )
            Transaction.objects.bulk_create(transactions)
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for all invoice ({', '.join([invoice_dict['invoice'] for invoice_dict in request.data['list_of_invoice']])}) paid by {request.user.full_name()} is approved"
            )
            # send confirmation mail to customer
            send_mail(
                PAYMENT_APPROVED_EMAIL_SUBJECT,
                f"Payment of {request.data['location']} is approved",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TEMPLATE,
                    {
                        'transaction_id': transaction_id,
                        'customer_id': request.user.braintree_customer_id,
                        'invoice': Transaction.objects.filter(transaction=transaction_id),
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            # send confirmation mail to calgary
            send_mail(
                f"Payment Approved - {account_number}",
                f"Payment of {request.data['location']} is approved",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TO_CALGARY_TEMPLATE,
                    {
                        'transaction_id': transaction_id,
                        'customer_id': request.user.braintree_customer_id,
                        'invoice': Transaction.objects.filter(transaction=transaction_id),
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            response = {
                'success': True,
                'status': status.HTTP_202_ACCEPTED,
                'message': PAYMENT_SUCCESSFUL_MESSAGE
            }
        else:
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for all invoice ({', '.join([invoice_dict['invoice'] for invoice_dict in request.data['list_of_invoice']])}) paid by {request.user.full_name()} denied"
            )
            list_of_invoice = []
            for invoice in request.data['invoice']:
                list_of_invoice.append(invoice['invoice'])
            invoices = ', '.join(list_of_invoice)
            # send denied mail to customer
            send_mail(
                PAYMENT_DENIED_EMAIL_SUBJECT,
                f"Payment of {request.data['location']} denied",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CUSTOMER_TEMPLATE,
                    {
                        'invoice': invoices,
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            # send denied mail to calgary
            send_mail(
                f"Payment Denied - {account_number}",
                f"Payment of {request.data['location']} denied",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CALGARY_TEMPLATE,
                    {
                        'invoice': invoices,
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': True
                    }
                )
            )
            response = {
                'error': True,
                'status': status.HTTP_406_NOT_ACCEPTABLE,
                'message': PAYMENT_DENIED_MESSAGE
            }
        return Response(response)


# Invoice list with address for All PDF
class ListOfInvoiceWithAddressView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_invoice_list_with_address(cus_no)
            return JsonResponse(data, safe=False)
        except ConnectionError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })


# -------------------------------------------------- QUOTATIONS ----------------------------------------------------
# Quotations View
class QuotationsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, status):
        if request.user.useraccess.quotes:
            try:
                cus_no = request.user.userprofile.account_number.account_number
                data = get_quotations(cus_no, status)
                return JsonResponse(data, safe=False)
            except NotFoundError:
                return JsonResponse({
                    'error': True,
                    'status': status.HTTP_404_NOT_FOUND,
                    'message': f'No record found for {cus_no} Account Number/Customer Number'
                })
            except ConnectionError:
                logger.error(ESC_DATABASE_CONNECTION_ERROR)
                return JsonResponse({
                    'error': True,
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': INTERNAL_SERVER_ERROR_500_MESSAGE
                })
            except ESCDataNotFetchingError:
                return JsonResponse({
                    'error': True,
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': INTERNAL_SERVER_ERROR_500_MESSAGE
                })
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'You have no permission for quotes'
            })


# Quotation List
class ListQuotationsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, loc_no, status):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_quotes_list(cus_no, loc_no, status)
            return JsonResponse(data, safe=False)
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })


# Show Quotes
class QuotesView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, loc_no, quote):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_quotes(cus_no, loc_no, quote)
            return JsonResponse(data, safe=False)
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })


# Payment of Quote
class PayQuoteView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if settings.BRAINTREE_PRODUCTION:
            braintree_env = braintree.Environment.Production
        else:
            braintree_env = braintree.Environment.Sandbox
        # configure Braintree
        braintree.Configuration.configure(
            braintree_env,
            merchant_id=settings.BRAINTREE_MERCHANT_ID,
            public_key=settings.BRAINTREE_PUBLIC_KEY,
            private_key=settings.BRAINTREE_PRIVATE_KEY
        )
        payment_method_nonce = request.data['payment_method_nonce']
        result = braintree.Transaction.sale({
            'amount': str(request.data['amount']),
            'payment_method_nonce': payment_method_nonce,
            'options': {
                'submit_for_settlement': True
            }
        })
        transaction_id = result.transaction.id
        account_number = request.user.userprofile.account_number.account_number
        gateway = get_gateway()
        card_details = gateway.transaction.find(transaction_id).credit_card_details.last_4
        if result.is_success:
            # update database
            transaction = Transaction.objects.create(
                transaction=transaction_id,
                user=request.user,
                status='success',
                amount=request.data['amount'],
                invoice=request.data['quote'],
                pay_for='quote',
                bt_status='submitted_for_settlement'
            )
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for Quote {transaction.invoice} paid by {request.user.full_name()} is approved"
            )
            # send confirmation mail to customer
            send_mail(
                PAYMENT_APPROVED_EMAIL_SUBJECT,
                f"Payment of {request.data['quote']} approved",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TEMPLATE,
                    {
                        'transaction_id': transaction.id,
                        'customer_id': transaction.user.braintree_customer_id,
                        'invoice': transaction.invoice,
                        'amount': transaction.amount,
                        'date': transaction.timestamp,
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': False
                    }
                )
            )
            # send confirmation mail to calgary
            send_mail(
                f"Payment Approved - {account_number}",
                f"Payment for {request.data['quote']} of {account_number} approved",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_APPROVED_TO_CALGARY_TEMPLATE,
                    {
                        'transaction_id': transaction.id,
                        'customer_id': transaction.user.braintree_customer_id,
                        'invoice': transaction.invoice,
                        'amount': transaction.amount,
                        'date': transaction.timestamp,
                        'account_number': account_number,
                        'card_detail': card_details,
                        'multiple': False
                    }
                )
            )
            response = {
                'success': True,
                'status': status.HTTP_202_ACCEPTED,
                'message': PAYMENT_SUCCESSFUL_MESSAGE
            }
        else:
            # create audit object
            Audit.objects.create(
                user=request.user,
                modifications=f"Payment for Quote {request.data['invoice']} paid by {request.user.full_name()} is denied"
            )
            # send denied mail to customer
            send_mail(
                PAYMENT_DENIED_EMAIL_SUBJECT,
                f"Payment of {request.data['quote']} denied",
                EMAIL_HOST_USER,
                [request.user.email],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CUSTOMER_TEMPLATE,
                    {
                        'invoice': request.data['invoice'],
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details
                    }
                )
            )

            # send denied mail to calgary
            send_mail(
                f"Payment Denied - {account_number}",
                f"Payment for {request.data['quote']} of {account_number} denied",
                EMAIL_HOST_USER,
                [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    PAYMENT_DENIED_TO_CALGARY_TEMPLATE,
                    {
                        'invoice': request.data['invoice'],
                        'amount': request.data['amount'],
                        'date': datetime.datetime.now(),
                        'account_number': account_number,
                        'card_detail': card_details
                    }
                )
            )
            response = {
                'error': True,
                'status': status.HTTP_406_NOT_ACCEPTABLE,
                'message': PAYMENT_DENIED_MESSAGE
            }
        return Response(response)


# --------------------------------------------------- SERVICE REQUEST ----------------------------------------------
# Service Request
class ServiceRequestDispatchesView(APIView):
    permission_classes = (IsAuthenticated,)

    # get list of location and address
    def get(self, request, loc_no):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_service_request_dispatches(cus_no, loc_no)
            data['email'] = request.user.email
            return JsonResponse(data, safe=False)
        except NotFoundError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_404_NOT_FOUND,
                'message': f'No record found for {cus_no} Account Number/Customer Number'
            })
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })

class ServiceRequestDispatchView(APIView):
    permission_classes = (IsAuthenticated,)

    # get list of location and address
    def get(self, request, dispatch_no):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_dispatch_parts(dispatch_no)
            data['email'] = request.user.email
            return JsonResponse(data, safe=False)
        except NotFoundError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_404_NOT_FOUND,
                'message': f'No record found for {dispatch_no} Dispatch Number/dispatch Number'
            })
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })

class ServiceRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    # get list of location and address
    def get(self, request):
        try:
            cus_no = request.user.userprofile.account_number.account_number
            data = get_service_request(cus_no)
            data['email'] = request.user.email
            return JsonResponse(data, safe=False)
        except NotFoundError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_404_NOT_FOUND,
                'message': f'No record found for {cus_no} Account Number/Customer Number'
            })
        except ConnectionError:
            logger.error(ESC_DATABASE_CONNECTION_ERROR)
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })

    # send mail for service request
    def post(self, request):
        if request.user.useraccess.service_request:
            # send email to calgary
            subject = f"Service Request for '{request.data['location']}' at '{request.data['address']}'"
            try:
                msg = EmailMultiAlternatives(
                    subject,
                    render_to_string(
                        'email/service_request_to_calgary.html',
                        {
                            'cus_no': request.user.userprofile.account_number.account_number,
                            'location': request.data['location'],
                            'address': request.data['address'],
                            'request': request.data['message']
                        }
                    ),
                    EMAIL_HOST_USER,
                    [settings.EMAIL_FOR_SERVICE_REQUEST]
                )
                msg.content_subtype = 'html'  # Main content is text/html
                msg.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
                with open(settings.STATIC_DIR + LOGO_PATH, 'rb') as f:
                    file = f.read()
                image = MIMEImage(file)
                image.add_header('Content-ID', '<logo.png>')
                msg.attach(image)
                msg.send()

            except Exception as e:
                print(e)
                logger.error(ESC_DATABASE_CONNECTION_ERROR)
                response = {
                    'error': True,
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': 'Something is wrong! Please try later or contact to Calgary Lock and Safe',
                    'error_msg': str(e)
                }
            else:
                response = {
                    'success': True,
                    'status': status.HTTP_200_OK,
                    'message': 'Service Request sent successfully'
                }
            return Response(response)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'You have no permission for service request'
            })


# ----------------------------------------------- DOWNLOAD PDF OF INVOICE ----------------------------------------
# function for download invoice pdf
def invoice_pdf_view(request, cus_no, loc_no, invoice):
    if request.method == 'GET':
        try:
            data = get_invoice(cus_no, loc_no, invoice)
            html = render_to_string('pdf/invoice.html', {
                'cus_no': data['cus_no'],
                'name': data['name'],
                'loc_name': data['loc_name'],
                'address': data['address'],
                'invoice': data['invoice'],
                'invoice_date': data['invoice_date'],
                'total': data['total'],
                'sub_total': data['sub_total'],
                'gst': float(data['total']) - float(data['sub_total']),
                'data': data['data'],
                'logo': settings.LOGO
            })
            
            output = pdfkit.from_string(html, output_path=False)
            response = HttpResponse(content_type="application/pdf")
            response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
            response.write(output)
            return response
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except Exception as e:
            logger.error('%s', e)
    else:
        return Response({'message': 'Not allowed'}, status.HTTP_400_BAD_REQUEST)


# function for download invoice pdf
def all_invoice_pdf_view(request, cus_no):
    if request.method == 'GET':
        try:
            data = get_invoice_list_with_address(cus_no)
            html = render_to_string('pdf/all_invoice.html', {
                'data': data,
                'logo': settings.LOGO
            })
            output = pdfkit.from_string(html, output_path=False)
            response = HttpResponse(content_type="application/pdf")
            response['Content-Disposition'] = 'attachment; filename="all_invoice.pdf"'
            response.write(output)
            return response
        except ESCDataNotFetchingError:
            return JsonResponse({
                'error': True,
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': INTERNAL_SERVER_ERROR_500_MESSAGE
            })
        except Exception as e:
            logger.error('%s', e)
    else:
        return Response({'message': 'Not allowed'}, status.HTTP_400_BAD_REQUEST)
