from django.contrib.auth.backends import ModelBackend

from .models import Employee


class EmployeeAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, login=None, **kwargs):
        login_value = login or username or kwargs.get(Employee.USERNAME_FIELD)
        if not login_value or password is None:
            return None

        try:
            user = Employee.objects.get(login=login_value)
        except Employee.DoesNotExist:
            return None

        if user.check_password(password):
            return user

        # Legacy plaintext passwords are upgraded on successful login.
        if user.password == password:
            user.set_password(password)
            user.save(update_fields=["password"])
            return user

        return None

    def get_user(self, user_id):
        try:
            return Employee.objects.get(pk=user_id)
        except Employee.DoesNotExist:
            return None
