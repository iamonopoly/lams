from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Same mechanism as Django's built-in password reset token, reused for
    two purposes: (1) lecturer email verification, (2) student initial
    password setup. We include is_active in the hash so a token is
    automatically invalidated the moment the account is activated —
    it can't be replayed afterward.
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"


account_activation_token = AccountActivationTokenGenerator()