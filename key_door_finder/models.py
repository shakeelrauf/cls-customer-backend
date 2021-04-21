from django.db import models
from django.conf import settings
from customer_dashboard.models import User

import random, string

# Create your models here.
class KeyQty(models.Model):
    file_number = models.CharField(max_length=255)
    key_id = models.CharField(max_length=255)
    category = models.CharField(max_length=255, null=True, blank=True)
    key_description = models.CharField(max_length=255, null=True, blank=True)
    key_above = models.CharField(max_length=255, null=True, blank=True)
    designation = models.CharField(max_length=255, null=True, blank=True)
    part_code = models.CharField(max_length=255, null=True, blank=True)
    stamping = models.CharField(max_length=255, null=True, blank=True)
    ship_separate = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    replaced = models.BooleanField(default=False)
    quantity = models.IntegerField()
    
    class Meta:
        db_table = 'KeyQty'

    def __str__(self):
        return self.key_id

class KeyGroup(models.Model):
    name = models.CharField(max_length=255, null=False)
    issue_date = models.DateTimeField(null=True)

    class Meta:
        db_table = 'KeyGroups'
    
    def __str__(self):
        return str(self.id) + str(self.name)

class KeyAuditReport(models.Model):
    run_at =  models.DateTimeField(null=True, blank=True, max_length=255)
    created_by =  models.ForeignKey(to=User, null=True , blank=True,on_delete=models.SET_NULL)
    audit_type = models.CharField(max_length=255, null=True, blank=True)
    confirm = models.BooleanField(default=False, null=True, blank=True)
    confirmed_at =  models.DateTimeField(null=True, blank=True, max_length=255)
    url = models.CharField(max_length=255, null=True, blank=True)

    def generate_url(self):
        self.url = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        return self.url
    
    def save(self, *args, **kwargs):
        url = self.generate_url()
        if KeyAuditReport.objects.filter(url=url):
            self.save()
        else:
            super(KeyAuditReport, self).save(*args, **kwargs)

class KeySequence(models.Model):
    file_number = models.CharField(max_length=255, null=True, blank=True)
    key_id = models.CharField(max_length=255, null=True, blank=True)
    sequence = models.IntegerField(null=True, blank=True)
    key_holder = models.CharField(max_length=255, null=True, blank=True)
    tenant_location = models.CharField(max_length=255, null=True, blank=True)
    date_issued = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    lost_key = models.BooleanField(default=False, null=True, blank=True)
    broken_key = models.BooleanField(default=False, null=True, blank=True)
    group = models.ForeignKey(to=KeyGroup,null=True, on_delete=models.SET_NULL)
    audit_report = models.ForeignKey(to=KeyAuditReport,null=True, on_delete=models.SET_NULL)
    class Meta:
        db_table = 'KeySequence'

    def __str__(self):
        return f"{self.key_id}-{self.sequence}"


class DoorsProMas(models.Model):
    file_number = models.CharField(max_length=255)
    door_number = models.CharField(max_length=255)
    stamping = models.CharField(max_length=255, null=True, blank=True)
    door_description = models.CharField(max_length=255, null=True, blank=True)
    area = models.CharField(max_length=255, null=True, blank=True)
    stage = models.CharField(max_length=255, null=True, blank=True)
    lock_part_num = models.CharField(max_length=255, null=True, blank=True)
    non_keyed = models.BooleanField(default=False)
    height = models.CharField(max_length=255)
    width = models.CharField(max_length=255)
    thickness = models.CharField(max_length=255)
    quantity = models.CharField(max_length=255, null=True, blank=True)
    diff_keying_side2 = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, null=True, blank=True)
    pinning_notes = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'DoorsProMas'

    def __str__(self):
        return self.door_number


class DPMCustomerDesc(models.Model):
    cus_description = models.CharField(max_length=255)
    file_number = models.CharField(max_length=255)
    door_number = models.CharField(max_length=255)

    class Meta:
        db_table = 'DPMCustomerDesc'

    def __str__(self):
        return self.door_number


class KeyingProMas(models.Model):
    file_number = models.CharField(max_length=255)
    door_number = models.CharField(max_length=255)
    position_type = models.CharField(max_length=255, null=True, blank=True)
    stamping = models.CharField(max_length=255, null=True, blank=True)
    key_number = models.CharField(max_length=255)

    class Meta:
        db_table = 'KeyingProMas'

    def __str__(self):
        return self.key_number


class Doors(models.Model):
    file_number = models.CharField(max_length=255)
    stamping = models.CharField(max_length=255, null=True, blank=True)
    door_number = models.CharField(max_length=255)
    door_type = models.CharField(max_length=255, null=True, blank=True)
    door_type_dimension = models.CharField(max_length=255, null=True, blank=True)
    door_lock_hw_lower = models.CharField(max_length=255, null=True, blank=True)
    door_lock_hw_upper = models.CharField(max_length=255, null=True, blank=True)
    door_lock_hw_backset = models.CharField(max_length=255, null=True, blank=True)
    door_lock_hw_lock_height_prep_lower = models.CharField(max_length=255, null=True, blank=True)
    door_lock_hw_lock_height_prep_upper = models.CharField(max_length=255, null=True, blank=True)
    door_closing_hw = models.CharField(max_length=255, null=True, blank=True)
    door_electrified_hw = models.CharField(max_length=255, null=True, blank=True)
    door_type_fire = models.BooleanField(default=False, null=True, blank=True)
    door_type_fire_rating = models.CharField(max_length=255, null=True, blank=True)
    door_type_window = models.CharField(max_length=255, null=True, blank=True)
    door_type_window_measurement = models.CharField(max_length=255, null=True, blank=True)
    door_handling = models.CharField(max_length=255, null=True, blank=True)
    door_accessory = models.CharField(max_length=255, null=True, blank=True)
    door_notes = models.CharField(max_length=255, null=True, blank=True)
    door_pic_out = models.BooleanField(default=False)
    door_pic_in = models.BooleanField(default=False)

    class Meta:
        db_table = 'Doors'

    def __str__(self):
        return self.door_number


class Frames(models.Model):
    file_number = models.CharField(max_length=255)
    stamping = models.CharField(max_length=255, null=True, blank=True)
    door_number = models.CharField(max_length=255)
    gps = models.CharField(max_length=255, null=True, blank=True)
    frame_type = models.CharField(max_length=255, null=True, blank=True)
    frame_type_dimension = models.CharField(max_length=255, null=True, blank=True)
    frame_type_fire = models.BooleanField(default=False, null=True, blank=True)
    frame_type_fire_rating = models.CharField(max_length=255, null=True, blank=True)
    frame_prep_strike_lower = models.CharField(max_length=255, null=True, blank=True)
    frame_prep_strike_upper = models.CharField(max_length=255, null=True, blank=True)
    frame_prep_hinge = models.CharField(max_length=255, null=True, blank=True)
    frame_prep_hinge_m1 = models.CharField(max_length=255, null=True, blank=True)
    frame_prep_hinge_m2 = models.CharField(max_length=255, null=True, blank=True)
    frame_prep_hinge_m3 = models.CharField(max_length=255, null=True, blank=True)
    frame_prep_hinge_m4 = models.CharField(max_length=255, null=True, blank=True)
    frame_notes = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'Frames'

    def __str__(self):
        return self.door_number


class HwPictures(models.Model):
    file_number = models.CharField(max_length=255)
    stamping = models.CharField(max_length=255, null=True, blank=True)
    door_number = models.CharField(max_length=255)
    door_pic_out = models.CharField(max_length=255, null=True, blank=True)
    door_pic_in = models.CharField(max_length=255, null=True, blank=True)
    door_out_img = models.ImageField(upload_to='hw_pic')
    door_in_img = models.ImageField(upload_to='hw_pic')

    class Meta:
        db_table = 'HwPictures'

    def __str__(self):
        return self.door_number


class KeyRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='key_request', on_delete=models.CASCADE)
    company = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    authorize_customer = models.CharField(max_length=255)
    purchase_order = models.CharField(max_length=255)

    delivery_method = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, default='pending')  # delivered, pending
    pickup_by = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.full_name()} - {self.company} - {self.authorize_customer} - {self.status}"


class KeyRequestQuantity(models.Model):
    key_request = models.ForeignKey(KeyRequest, related_name='requests', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    key_code = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key_request.user.full_name()} - {self.quantity} - {self.brand}"


class KeyRequestImage(models.Model):
    key_request = models.ForeignKey(KeyRequest, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='key_request', null=True, blank=True)

    def __str__(self):
        return self.key_request
