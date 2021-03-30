from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from django.core.mail import send_mail
from customer_dashboard.models import UserProfile
from customer_dashboard.serializers import UserSerializer, FileNumberSerializer
from key_door_finder.models import KeyQty, KeySequence, KeyGroup
from key_door_finder.serializers import KeyQtySerializer,KeyGroupSerializer, EditKeySequenceSerializer, ActionKeySequenceSerializer, \
    KeySequenceSerializer, KeyRequestSerializer, AllKeyQtySerializer
from django.conf.global_settings import EMAIL_HOST_USER
from django.conf import settings
import logging
import pdfkit
import csv
import sqlite3
from django.http import HttpResponse
from django.db.models import Q
from django.template.loader import render_to_string
import pdb
import json
logger = logging.getLogger(__name__)
NO_PERMISSOIN_MANAGE_KEYS_MESSAGE = 'You have no permission for manage keys'


# when click on view keys (list of all keys of all file numbers which is assigned to user)
class KeyQtyView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user_data = UserSerializer(request.user).data
        file_number_instance = request.user.userprofile.file_numbers.all()
        current_user_info = {
            'id': user_data['id'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'last_login': user_data['last_login'],
            'last_modified': user_data['last_modified']
        }
        if file_number_instance:
            if request.query_params.get('file_number') != 'all':
                key_qty = KeyQty.objects.filter(file_number=request.query_params['file_number'])
            elif request.query_params.get('file_number'):
                key_qty = KeyQty.objects.filter(file_number=file_number_instance[0])

            results = self.paginate_queryset(key_qty, request, view=self)
            serializer = KeyQtySerializer(results, many=True)
            response = {
                'current_user': current_user_info,
                'file_numbers': FileNumberSerializer(file_number_instance, many=True).data,
                'selected': FileNumberSerializer(file_number_instance[0]).data,
                'data': serializer.data
            }
            return self.get_paginated_response(response)
        else:
            response = {
                'current_user': current_user_info,
                'file_numbers': FileNumberSerializer(file_number_instance, many=True).data,
                'selected': '',
                'data': []
            }
            return Response(response)


class KeyGroupsView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    def get(self, request):
        user_data = UserSerializer(request.user).data
        current_user_info = {
            'id': user_data['id'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'last_login': user_data['last_login'],
            'last_modified': user_data['last_modified']
        }

        key_groups = KeyGroup.objects.all()
        keys = KeySequence.objects.filter(group=None)
        results = self.paginate_queryset(key_groups, request, view=self)
        serializer = KeyGroupSerializer(results, many=True)
        response = {
            'current_user': current_user_info,
            'data': serializer.data,
            'keys': KeySequenceSerializer(keys, many=True).data
        }

        return self.get_paginated_response(response)

    def post(self, request):
        kyes_ids = request.data.get('keys')
        name = request.data.get('name')
        user = request.data.get('user')
        issue_date = request.data.get('issueDate')
        key_group = KeyGroup.objects.create(name=name, issue_date=issue_date )
        keys_sequences = KeySequence.objects.filter(pk__in=kyes_ids)
        keys_sequences.update(group=key_group.id, key_holder=user)
        return Response({'success': True})

    def delete(self, request):
        group_id = request.data.get('id')
        KeyGroup.objects.filter(pk=group_id).delete()
        return Response({'success': True})
        
class KeyGroupView(APIView):
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, id):
        name = request.data.get('name')
        user = request.data.get('user')
        issue_date = request.data.get('issueDate')
        key_group = KeyGroup.objects.filter(id=id)
        key_group.update(name=name, issue_date=issue_date)
        KeySequence.objects.filter(group=id).update(group=None, key_holder='')
        keys_ids = request.data.get('keys')
        keys_sequences = KeySequence.objects.filter(pk__in=keys_ids)
        keys_sequences.update(group=key_group[0].id, key_holder=user)
        return Response({'success': True})
        
class RemoveKeySequenceFromKeyGroup(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        id = request.data.get('id')
        sequence = KeySequence.objects.filter(id=id).update(group=None, key_holder='')
        return Response({'success': True})

# for update key sequence table
class KeySequenceView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_instance(self, request, pk):
        try:
            if KeySequence.objects.get(id=pk).file_number in [
                f.file_number for f in request.user.userprofile.file_numbers.all()
            ]:
                return KeySequence.objects.get(id=pk)
            # if not then return none
            else:
                return None
        except KeySequence.DoesNotExist:
            return None

    # for edit key sequence data (key holder, tenant name, email, phone, issued date etc)
    def put(self, request, pk):  # pk is key sequence id
        if request.user.useraccess.key_finder:
            instance = self.get_instance(request, pk)  # instance of key sequence
            if instance:
                try:
                    serializer = EditKeySequenceSerializer(instance, data=request.data, context={'request': request})
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                        response = {'success': True, 'status': status.HTTP_200_OK, 'data': serializer.data}
                except Exception as e:
                    logger.error("%s", e)
                    response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'data': serializer.errors}
            else:
                response = {'error': True, 'status': status.HTTP_404_NOT_FOUND, 'message': 'Not Found'}
            return Response(response)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': NO_PERMISSOIN_MANAGE_KEYS_MESSAGE
            })

    # for actions (lost and broken keys)
    def patch(self, request, pk):  # pk is key sequence id
        if request.user.useraccess.key_finder:
            instance = self.get_instance(request, pk)
            if instance:
                try:
                    serializer = ActionKeySequenceSerializer(instance, data=request.data, context={'request': request})
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                        key_stamp = instance.key_id + " - "+ str(instance.sequence)
                        send_mail(
                            "Key Status - Calgary Lock and Safe",
                            f"Status of Key(s) for {key_stamp} by {request.user.full_name()}",
                            EMAIL_HOST_USER,
                            [request.user.email, instance.email,settings.EMAIL_TO_CALGARY_REPORTS],
                            html_message=render_to_string(
                                'email/key_status_updated.html',
                                {
                                    'data': instance,
                                    'key_stamp': key_stamp
                                }
                            )
                        )
                        response = {'success': True, 'status': status.HTTP_200_OK, 'data': serializer.data}
                except Exception as e:
                    logger.error('%s', e)
                    response = {'error': True, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'data': serializer.errors}
            else:
                response = {'error': True, 'status': status.HTTP_404_NOT_FOUND, 'message': 'Not Found'}
            return Response(response)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': NO_PERMISSOIN_MANAGE_KEYS_MESSAGE
            })


# export csv file (only for particular key id) (now not in use)
class ExportCSVKeySequence(APIView):

    def get(self, request, user_id, file_num, qty_id):
        # check user have system number or key
        if UserProfile.objects.get(user__id=user_id).file_numbers.filter(file_number=file_num).exists():
            try:
                qty_obj = KeyQty.objects.get(id=qty_id)
            except KeyQty.DoesNotExist:
                qty_obj = None
            if qty_obj:
                file_number, key_id = qty_obj.file_number, qty_obj.key_id
                seq_data = KeySequence.objects.filter(file_number=file_number, key_id=key_id)

                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f"attachment; filename={key_id}.csv"
                fields = [f.get_attname() for f in KeySequence._meta.fields]
                fields.remove('id')
                writer = csv.DictWriter(response, fieldnames=fields)
                writer.writeheader()
                for seq in seq_data:
                    data = {}
                    for field in fields:
                        data[field] = getattr(seq, field)
                    writer.writerow(data)
                return response
            else:
                response = {'error': True, 'status': status.HTTP_404_NOT_FOUND}
                return Response(response)
        else:
            response = {'error': True, 'status': status.HTTP_401_UNAUTHORIZED}
            return Response(response)


# export system csv file (for particular system or file number) (now not in use)
class ExportSystemCSVKeySequence(APIView):

    def get(self, request, user_id, file_num):
        # check user have system or key
        if UserProfile.objects.get(user__id=user_id).file_numbers.filter(file_number=file_num).exists():
            try:
                qty = KeyQty.objects.filter(file_number=file_num)
            except KeySequence.DoesNotExist:
                qty = None
            if qty:
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f"attachment; filename={file_num}.csv"
                fields = [f.get_attname() for f in KeyQty._meta.fields]
                fields.remove('id')
                writer = csv.DictWriter(response, fieldnames=fields)
                writer.writeheader()
                for q in qty:
                    data = {}
                    for field in fields:
                        data[field] = getattr(q, field)
                    writer.writerow(data)
                return response
            else:
                response = {'error': True, 'status': status.HTTP_404_NOT_FOUND}
                return Response(response)
        else:
            response = {'error': True, 'status': status.HTTP_401_UNAUTHORIZED}
            return Response(response)


def key_sequence_pdf(request, user_id, file_num, qty_id):
    if request.method == 'GET':
        if UserProfile.objects.get(user__id=user_id).file_numbers.filter(file_number=file_num).exists():
            try:
                qty_obj = KeyQty.objects.get(id=qty_id)
            except KeyQty.DoesNotExist:
                qty_obj = None
            if qty_obj:
                data = KeySequence.objects.filter(file_number=file_num, key_id=qty_obj.key_id)
                html = render_to_string('pdf/sequence.html', {
                    'data': data
                })
                output = pdfkit.from_string(html, output_path=False)
                response = HttpResponse(content_type="application/pdf")
                response['Content-Disposition'] = f"attachment; filename={qty_obj.key_id}.pdf"
                response.write(output)
                return response
    else:
        return Response({'message': 'Not allowed'}, status.HTTP_400_BAD_REQUEST)


def system_pdf(request, user_id, file_num):
    if request.method == 'GET':
        if UserProfile.objects.get(user__id=user_id).file_numbers.filter(file_number=file_num).exists():
            try:
                if file_num == 'all':
                    qty = KeyQty.objects.filter(file_number__in=UserProfile.objects.get(user__id=user_id).file_numbers.all())
                else:
                    qty = KeyQty.objects.filter(file_number=file_num)
            except KeySequence.DoesNotExist:
                qty = None
            if qty:
                html = render_to_string('pdf/quantity.html', {
                    'data': qty
                })
                output = pdfkit.from_string(html, output_path=False)
                response = HttpResponse(content_type="application/pdf")
                response['Content-Disposition'] = f"attachment; filename={file_num}.pdf"
                response.write(output)
                return response
    else:
        return Response({'message': 'Not allowed'}, status.HTTP_400_BAD_REQUEST)


class KeySequenceListView(APIView):
    permission_classes = (IsAuthenticated,)

    def check_user(self, request, file_number):
        return request.user.userprofile.file_numbers.filter(file_number=file_number).exists()

    def get(self, request, file_number, key_id):
        if self.check_user(request, file_number):
            queryset = KeySequence.objects.filter(file_number=file_number, key_id=key_id).order_by('key_id')
            serializer = KeySequenceSerializer(queryset, many=True)
            response = {
                'success': True,
                'status': status.HTTP_200_OK,
                'door_compromised': KeySequence.objects.filter(
                    Q(key_id=key_id) & (Q(lost_key=True) | Q(broken_key=True))
                ).count(),
                'data': serializer.data
            }
        else:
            response = {
                'error': False,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'You are not authorized person of this file number or file number does not exist'
            }
        return Response(response)


# api for download all key list of file number (CSV and PDF)
class AllKeyQuantityView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if request.user.useraccess.key_finder:
            file_number_instance = request.user.userprofile.file_numbers.all()

            if request.query_params.get('file_number') != 'all':
                key_qty = KeyQty.objects.filter(file_number=request.query_params['file_number'])
            elif request.query_params.get('file_number'):
                key_qty = KeyQty.objects.filter(file_number__in=[f.file_number for f in file_number_instance])
            serializer = AllKeyQtySerializer(key_qty, many=True)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': NO_PERMISSOIN_MANAGE_KEYS_MESSAGE
            })


# for key request
class KeyRequestView(APIView):
    permission_classes = (IsAuthenticated,)
    # parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        if request.user.useraccess.key_finder:
            print('req data', request.data)
            try:
                serializer = KeyRequestSerializer(data=request.data, context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    return Response({'message': 'Key request submitted successfully'}, status.HTTP_200_OK)
            except Exception as e:
                print(e)
                return Response({'message': 'Something went wrong! Please try later'},
                                status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'error': True,
                'status': status.HTTP_400_BAD_REQUEST,
                'message': NO_PERMISSOIN_MANAGE_KEYS_MESSAGE
            })
