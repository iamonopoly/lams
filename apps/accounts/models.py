from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

# Matches: PS/CSC/22/0001  (Faculty/Dept/Year/4-digit number)
reg_number_validator = RegexValidator(
    regex=r"^[A-Z]{2,4}/[A-Z]{2,5}/\d{2}/\d{4}$",
    message="Registration number must be in the format PS/CSC/22/0001.",
)


class UserManager(BaseUserManager):
    """
    Custom manager required because we use email instead of username
    as the login identifier (AbstractBaseUser has no default manager
    that understands that).
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # student accounts start with no password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if not password:
            raise ValueError("Superusers must have a password.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Both students and lecturers are rows in this same table, distinguished
    by `role`. Login is always by email + password — registration number is
    only used once, at student sign-up, to verify identity against the
    roster. It is never a login credential.

    `is_active=False` by default: students activate via the password-setup
    link, lecturers activate via the email-verification link.
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        LECTURER = "LECTURER", "Lecturer"
        ADMIN = "ADMIN", "Administrator"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_lecturer(self):
        return self.role == self.Role.LECTURER

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN


class PreRegisteredStudent(models.Model):
    """
    The 'lecturer-uploaded student list' a registration number must appear
    in before that student can create an account.

    For now this is populated manually via /admin/. In Module 3, the Excel
    roster upload writes to this same table — the registration check
    doesn't change, only how the table gets filled.
    """

    reg_number = models.CharField(
        max_length=20, unique=True, validators=[reg_number_validator]
    )
    full_name = models.CharField(max_length=150)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reg_number"]

    def __str__(self):
        return f"{self.reg_number} — {self.full_name}"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    reg_number = models.CharField(
        max_length=20, unique=True, validators=[reg_number_validator]
    )

    def __str__(self):
        return self.reg_number


class LecturerProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="lecturer_profile"
    )
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.email