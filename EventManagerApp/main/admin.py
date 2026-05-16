from django.contrib import admin
from .models import Contractor, Employee, Feedback
# Register your models here.
admin.site.register(Employee)
admin.site.register(Contractor)
admin.site.register(Feedback)
