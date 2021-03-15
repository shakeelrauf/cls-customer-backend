import os
import schedule
import time
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calgary_web_portal.settings')

import django
django.setup()

from email.mime.image import MIMEImage
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf.global_settings import EMAIL_HOST_USER
from django.conf import settings
from django.template.loader import render_to_string

from customer_dashboard.braintree import get_gateway
from customer_dashboard.models import UserProfile, AccountNumber, Transaction


def off_for_children_users(parent_user):
    users = parent_user.children.all()
    print('children', users)
    if users:
        for user in users:
            user.useraccess.key_finder = False
            user.useraccess.door_finder = False
            user.useraccess.save()
            print('parent_user', user)
            usrs = user.children.all()
            if usrs:
                off_for_children_users(user)
    return None


def check_subscription():
    print('Run Check Subscription')
    accounts = AccountNumber.objects.all()
    for account in accounts:
        print('account', account)
        # if subscription is expire today (send mail to primary user and calgary)
        if account.is_registered and account.exp_date and account.exp_date < datetime.date.today():
            # get user profile object
            try:
                user_profile = UserProfile.objects.get(user__user_type='primary', account_number=account)
            except UserProfile.DoesNotExist:
                print('*' * 80)
                print('if', account)
                print('*' * 80)
            else:
                # get user object
                user_access = user_profile.user.useraccess
                # set paid services off
                if user_access.key_finder and user_access.door_finder:
                    user_access.key_finder = False
                    user_access.door_finder = False
                    user_access.save()
                    print('parent', user_profile.user)
                    off_for_children_users(user_profile.user)
                    # send mail to customer
                    subject_customer = 'Calgary Lock and Safe'
                    message_customer = 'Calgary services expire today'

                    msg = EmailMultiAlternatives(
                        subject_customer,
                        render_to_string(
                            'email/service_expire_today.html',
                            {
                                'full_name': user_profile.user.full_name(),
                                'account_number': account.account_number,
                                'first_name': user_profile.user.first_name,
                                'last_name': user_profile.user.last_name,
                                'phone': user_profile.user.phone,
                                'file_numbers': user_profile.file_numbers.all()
                            }
                        ),
                        EMAIL_HOST_USER,
                        [user_profile.user.email]
                    )
                    msg.content_subtype = 'html'  # Main content is text/html
                    msg.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
                    with open(settings.STATIC_DIR + '/images/logo.png', 'rb') as f:
                        file = f.read()
                    image = MIMEImage(file)
                    image.add_header('Content-ID', '<logo.png>')
                    msg.attach(image)
                    msg.send()

                    # send mail to calgary
                    subject_calgary = f"{account.account_number} - {user_profile.user.full_name()}"
                    message_calgary = f"{account.account_number} expire today"
                    send_mail(
                        subject_calgary, message_calgary, EMAIL_HOST_USER, [settings.EMAIL_TO_CALGARY],
                        html_message=render_to_string(
                            'email/service_expire_today_to_calgary.html',
                            {
                                'account_number': account.account_number,
                                'first_name': user_profile.user.first_name,
                                'last_name': user_profile.user.last_name,
                                'phone': user_profile.user.phone,
                                'file_numbers': user_profile.file_numbers.all()
                            }
                        )
                    )

        # 7 days before expiration of subscription (send mail to primary user and calgary)
        elif account.is_registered and account.exp_date - datetime.timedelta(days=7) == datetime.datetime.today():
            try:
                user_profile = UserProfile.objects.get(user__user_type='primary', account_number=account)
            except UserProfile.DoesNotExist:
                print('*' * 80)
                print('else', account)
                print('*' * 80)

            # send mail to customer
            subject_customer = 'Calgary Lock and Safe'
            message_customer = 'Calgary services expire after 7 days'

            msg = EmailMultiAlternatives(
                subject_customer,
                render_to_string(
                    'email/service_expire_after_7_days.html',
                    {
                        'full_name': user_profile.user.full_name(),
                        'account_number': account.account_number,
                        'expire_date': account.exp_date,
                        'first_name': user_profile.user.first_name,
                        'last_name': user_profile.user.last_name,
                        'phone': user_profile.user.phone,
                        'file_numbers': user_profile.file_numbers.all()
                    }
                ),
                EMAIL_HOST_USER,
                [user_profile.user.email],
            )
            msg.content_subtype = 'html'  # Main content is text/html
            msg.mixed_subtype = 'related'  # This is critical, otherwise images will be displayed as attachments
            with open(settings.STATIC_DIR + '/images/logo.png', 'rb') as f:
                file = f.read()
            image = MIMEImage(file)
            image.add_header('Content-ID', '<logo.png>')
            msg.attach(image)
            msg.send()

            # send mail to calgary
            subject_calgary = f"{account.account_number} - {user_profile.user.full_name()}"
            message_calgary = f"{account.account_number} expires at {account.exp_date}"
            send_mail(
                subject_calgary, message_calgary, EMAIL_HOST_USER, [settings.EMAIL_TO_CALGARY],
                html_message=render_to_string(
                    'email/service_expire_after_7_days_to_calgary.html',
                    {
                        'account_number': account.account_number,
                        'expire_date': account.exp_date,
                        'first_name': user_profile.user.first_name,
                        'last_name': user_profile.user.last_name,
                        'phone': user_profile.user.phone,
                        'file_numbers': user_profile.file_numbers.all()
                    }
                )
            )


def update_braintree_status():
    print('run braintree status updation code')
    gateway = get_gateway()
    payments = Transaction.objects.exclude(bt_status='settled')
    for payment in payments:
        try:
            payment.bt_status = gateway.transaction.find(payment.transaction).status
            payment.save()
        except Exception as e:
            print('*' * 80)
            print(e)
            print('*' * 80)
            pass


def run_task():
    print('start run')
    schedule.every().day.at("00:05").do(check_subscription)
    schedule.every().minute.do(update_braintree_status)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    run_task()
