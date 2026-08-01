from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import StudentProfile


class RegNumberOrEmailBackend(ModelBackend):
    """
    Lets a student log in with their registration number instead of
    email, while lecturers (who have no reg number) keep using email —
    both go through the same login form/field.

    Detection is simple: an identifier containing "@" is treated as an
    email; anything else is looked up as a registration number via
    StudentProfile. Subclassing ModelBackend (rather than writing a
    bare BaseBackend) means get_user() and permission-checking methods
    are inherited for free — only authenticate() needs to change.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        User = get_user_model()
        identifier = username.strip()

        try:
            if "@" in identifier:
                user = User.objects.get(email__iexact=identifier)
            else:
                reg_number = identifier.upper()
                user = StudentProfile.objects.select_related("user").get(
                    reg_number=reg_number
                ).user
        except (User.DoesNotExist, StudentProfile.DoesNotExist):
            # Run the hasher anyway on a dummy password — same timing-attack
            # mitigation ModelBackend itself uses when the user isn't found.
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None