from django.urls import path
from customer_dashboard import views

urlpatterns = [
    # create primary user account
    path('create/primary/', views.CreateNewPrimaryUserView.as_view(), name='create_primary_user'),

    # login, reset password and change password
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('reset/password/', views.ResetPasswordView.as_view(), name='reset_password'),
    # path('confirm/password/', views.ConfirmResetPassword.as_view(), name='confirm_password'),
    path('change/password/', views.ChangePasswordView.as_view(), name='change_password'),

    # manage user
    path('manage/user/', views.AdditionalUserView.as_view(), name='add_new_additional_user'),
    path('manage/user/<int:pk>/', views.AdditionalUserView.as_view(), name='update_delete_additional_user'),
    path('audit/', views.AuditView.as_view(), name='audits'),
    path('user/file-numbers/', views.FileNumbersView.as_view(), name='file_numbers_list'),

    # company details
    path('company/details/', views.CompanyDetailsView.as_view(), name='company_details'),
    path('company/update_details/<custNo>/<locNo>', views.CompanyDetailsView.as_view(), name='update_company_details'),

    # accounting
    path('accounting/', views.AccountingView.as_view(), name='accounting'),
    path('accounting/invoice/list/<str:loc_no>/', views.ListInvoiceView.as_view(), name='invoice_list'),
    path('accounting/invoice/<str:loc_no>/<str:invoice>/', views.InvoiceView.as_view(), name='invoice'),
    path('accounting/help/', views.CustomerHelpAccountingView.as_view(), name='customer_help'),
    path('accounting/all/invoice/', views.ListOfInvoiceWithAddressView.as_view(), name='invoice_list_with_address'),

    # quotations
    path('quotations/<str:status>/', views.QuotationsView.as_view(), name='quotations'),
    path('quotations/list/<str:loc_no>/<str:status>/', views.ListQuotationsView.as_view(), name='quotes_list'),
    path('quotations/detail/<str:loc_no>/<str:quote>/', views.QuotesView.as_view(), name='quote_detail'),

    # service request
    path('service-request/', views.ServiceRequestView.as_view(), name='service_request'),

    # file number naming
    path('file-numbers/', views.FileNumbersView.as_view(), name='file_numbers'),
    path('file-numbers/<int:pk>/', views.FileNumbersView.as_view(), name='file_number'),

    # payment gateway
    path('get-payment-token/', views.GetTokenForPaymentView.as_view(), name='get_token'),
    path('invoice/payment/', views.PayInvoiceView.as_view(), name='pay_invoice'),
    path('invoice/payment/<str:loc_no>/', views.PayInvoiceForLocationView.as_view(), name='pay_invoice_for_location'),
    path('invoice/all/payment/', views.PayAllInvoiceView.as_view(), name='pay_all_invoice'),
    path('quote/payment/', views.PayQuoteView.as_view(), name='pay_quote'),

    # braintree webhook
    # path('status/webhook/', BraintreeWebhookView.as_view(), name='braintree_webhook'),

    # download invoice pdf
    path('pdf/invoice/<str:cus_no>/<str:loc_no>/<str:invoice>/', views.invoice_pdf_view, name='invoice'),
    path('pdf/all/invoice/<str:cus_no>/', views.all_invoice_pdf_view, name='all_invoice'),
]
