from django.db import transaction
from django.db.models import Q
from django.conf.global_settings import EMAIL_HOST_USER
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from rest_framework import serializers

from key_door_finder.models import KeyQty, KeyGroup, KeySequence, KeyRequest, KeyRequestQuantity, KeyRequestImage
from customer_dashboard.models import Audit


class KeySequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeySequence
        fields = '__all__'
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['name'] = str(instance)
        return response

class KeyGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyGroup
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        query = KeySequence.objects.filter(group=instance.id)
        response['sequence'] = KeySequenceSerializer(query, many=True).data
        return response


class KeyQtySerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyQty
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        query = KeySequence.objects.filter(key_id=instance.key_id, file_number=instance.file_number)
        response['door_compromised'] = KeySequence.objects.filter(
            Q(key_id=instance.key_id) & Q(file_number=instance.file_number) & (
                Q(lost_key=True) 
            )
        ).count()
        response['sequence'] = KeySequenceSerializer(query, many=True).data
        return response


class AllKeyQtySerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyQty
        fields = '__all__'


class EditKeySequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeySequence
        fields = ['key_holder', 'tenant_location', 'date_issued', 'phone', 'email']


class ActionKeySequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeySequence
        fields = ['lost_key', 'broken_key']


class KeyRequestQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyRequestQuantity
        fields = ['quantity', 'key_code', 'brand']


class KeyRequestImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyRequestImage
        fields = ['image']


class KeyRequestSerializer(serializers.ModelSerializer):
    # key_request_quantity = KeyRequestQuantitySerializer()
    key_request_quantity = serializers.ListField(write_only=True, source='requests')
    # key_images = KeyRequestImageSerializer(source='images', many=True, read_only=True)

    def create(self, validated_data):
        with transaction.atomic():
            # keys = validated_data.pop('key_request_quantity')
            keys = validated_data.pop('requests')
            # images = validated_data.pop('images')
            # images = self.context.get('view').request.FILES
            # images = self.context['request'].FILES
            validated_data['user'] = self.context['request'].user
            validated_data['status'] = 'pending'
            key_request = KeyRequest.objects.create(**validated_data)
            requested_keys = []
            # create KeyRequestQuantity objects
            for key in keys:
                requested_keys.append(
                    KeyRequestQuantity(
                        key_request=key_request,
                        quantity=key['quantity'],
                        key_code=key['key_code'],
                        brand=key['brand']
                    )
                )
            KeyRequestQuantity.objects.bulk_create(requested_keys)
            # # create KeyRequestImage objects
            # key_images = []
            # for image in images:
            #     key_images.append(
            #         KeyRequestImage(
            #             key_request=key_request,
            #             image=image
            #         )
            #     )
            # KeyRequestImage.objects.bulk_create(key_images)
            key_list = [key.key_code for key in requested_keys]
            if len(key_list) == 1:
                record = f"key {requested_keys[0].key_code}"
            else:
                record = f"keys ({', '.join(key_list)})"
            # create audit object
            Audit.objects.create(
                user=self.context['request'].user,
                modifications=f"{self.context['request'].user} requested for {record}"
            )

            # sending mail to customer
            send_mail(
                "Key Request - Calgary Lock and Safe",
                f"Order of Key(s) for {self.context['request'].user.userprofile.account_number.account_number} by {self.context['request'].user.full_name()}",
                EMAIL_HOST_USER,
                [self.context['request'].user.email],
                html_message=render_to_string(
                    'email/key_request_to_customer.html',
                    {
                        'date': key_request.timestamp,
                        'company': key_request.company,
                        'phone': key_request.phone,
                        'address': key_request.address,
                        'email': key_request.email,
                        'order_number': key_request.purchase_order,
                        'pickup_by': key_request.pickup_by,
                        'courier': '',
                        'authorize_name': key_request.authorize_customer,
                        'keys': KeyRequestQuantity.objects.filter(key_request=key_request)
                    }
                )
            )

            # sending mail to calgary
            send_mail(
                "Key Request - Calgary Lock and Safe",
                f"Order of Key(s) for {self.context['request'].user.userprofile.account_number.account_number} by {self.context['request'].user.full_name()}",
                EMAIL_HOST_USER,
                [settings.EMAIL_FOR_SERVICE_REQUEST],
                html_message=render_to_string(
                    'email/key_request_to_calgary.html',
                    {
                        'date': key_request.timestamp,
                        'company': key_request.company,
                        'phone': key_request.phone,
                        'address': key_request.address,
                        'email': key_request.email,
                        'order_number': key_request.purchase_order,
                        'pickup_by': key_request.pickup_by,
                        'courier': '',
                        'authorize_name': key_request.authorize_customer,
                        'keys': KeyRequestQuantity.objects.filter(key_request=key_request)
                    }
                )
            )
        return key_request

    class Meta:
        model = KeyRequest
        fields = ['company', 'address', 'phone', 'email', 'authorize_customer', 'purchase_order', 'delivery_method',
                  'timestamp', 'status', 'pickup_by', 'key_request_quantity']
