from django.urls import path
from key_door_finder import views

urlpatterns = [
    # key quantity
    path('keys/', views.KeyQtyView.as_view(), name='view_keys'),
    path('keys/all/', views.AllKeyQuantityView.as_view(), name='all_keys'),
    # key groupings
    path('keysgroups/', views.KeyGroupsView.as_view(), name="view_key_groupings"),
    path('keysgroups/group/<id>', views.KeyGroupView.as_view(), name="view_key_grouping"),
    path('keysgroups/remove_item', views.RemoveKeySequenceFromKeyGroup.as_view(), name="remove_view_key_grouping"),
    # key sequence
    path('sequence/<int:pk>/', views.KeySequenceView.as_view(), name='key_sequence'),
    path('sequence/export/csv/<int:pk>/', views.ExportCSVKeySequence.as_view(), name='export_key_sequence'),
    path('sequence/export/system/csv/<str:file_num>/', views.ExportSystemCSVKeySequence.as_view(),
         name='export_system_key_sequence'),
    path('sequence/<str:file_number>/<str:key_id>/', views.KeySequenceListView.as_view(), name='key_sequence'),

    # key request
    path('key-request/', views.KeyRequestView.as_view(), name='key_request'),

    # CSV files
    path('csv/key-sequence/<int:user_id>/<str:file_num>/<int:qty_id>/', views.ExportCSVKeySequence.as_view(),
         name='csv_key_sequence'),
    path('csv/key-qty/<int:user_id>/<str:file_num>/', views.ExportSystemCSVKeySequence.as_view(), name='csv_key_qty'),

    # pdf files
    path('pdf/key-sequence/<int:user_id>/<str:file_num>/<int:qty_id>/', views.key_sequence_pdf,
         name='pdf_key_sequence'),
    path('pdf/key-qty/<int:user_id>/<str:file_num>/', views.system_pdf, name='csv_key_qty'),
]
