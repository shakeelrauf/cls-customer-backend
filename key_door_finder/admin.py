from django.contrib import admin
from .models import KeyQty, KeySequence, DoorsProMas, KeyingProMas, Doors, Frames, HwPictures, DPMCustomerDesc, \
    KeyRequest, KeyRequestQuantity, KeyRequestImage


# Register your models here.
class KeyQtyAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_number', 'key_id', 'category', 'key_description', 'key_above', 'designation',
                    'part_code', 'stamping', 'ship_separate', 'disabled', 'replaced', 'quantity']


class KeySequenceAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_number', 'key_id', 'sequence', 'key_holder', 'tenant_location', 'date_issued',
                    'phone', 'email', 'lost_key', 'broken_key']


class DoorsProMasAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_number', 'door_number', 'stamping', 'door_description', 'area', 'stage',
                    'lock_part_num', 'non_keyed', 'height', 'width', 'thickness', 'quantity', 'diff_keying_side2',
                    'notes', 'pinning_notes']


class DPMCustomerDescAdmin(admin.ModelAdmin):
    list_display = ['id', 'cus_description', 'file_number', 'door_number']


class KeyingProMasAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_number', 'door_number', 'position_type', 'stamping', 'key_number']


class DoorsAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_number', 'door_number', 'door_type', 'door_type_dimension', 'door_lock_hw_lower',
                    'door_lock_hw_upper', 'door_lock_hw_backset', 'door_lock_hw_lock_height_prep_lower',
                    'door_lock_hw_lock_height_prep_upper', 'door_closing_hw', 'door_electrified_hw', 'door_type_fire',
                    'door_type_fire_rating', 'door_type_window', 'door_type_window_measurement', 'door_handling',
                    'door_accessory', 'door_notes', 'door_pic_out', 'door_pic_in', 'stamping']


class FramesAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_number', 'door_number', 'gps', 'frame_type', 'frame_type_dimension', 'frame_type_fire',
                    'frame_type_fire_rating', 'frame_prep_strike_lower', 'frame_prep_strike_upper', 'frame_prep_hinge',
                    'frame_prep_hinge_m1', 'frame_prep_hinge_m2', 'frame_prep_hinge_m3', 'frame_prep_hinge_m4',
                    'frame_notes', 'stamping']


class HwPicturesAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_number', 'door_number', 'door_pic_out', 'door_pic_in', 'stamping']


class KeyRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'company', 'address', 'email', 'phone', 'authorize_customer', 'purchase_order',
                    'delivery_method', 'timestamp', 'status', 'pickup_by']


class KeyRequestQuantityAdmin(admin.ModelAdmin):
    list_display = ['id', 'key_request', 'quantity', 'key_code', 'brand']


class KeyRequestImagesAdmin(admin.ModelAdmin):
    list_display = ['id', 'key_request', 'image']


# register with admin app
admin.site.register(KeyQty, KeyQtyAdmin)
admin.site.register(KeySequence, KeySequenceAdmin)
admin.site.register(DoorsProMas, DoorsProMasAdmin)
admin.site.register(DPMCustomerDesc, DPMCustomerDescAdmin)
admin.site.register(KeyingProMas, KeyingProMasAdmin)
admin.site.register(Doors, DoorsAdmin)
admin.site.register(Frames, FramesAdmin)
admin.site.register(HwPictures, HwPicturesAdmin)
admin.site.register(KeyRequest, KeyRequestAdmin)
admin.site.register(KeyRequestQuantity, KeyRequestQuantityAdmin)
admin.site.register(KeyRequestImage, KeyRequestImagesAdmin)
