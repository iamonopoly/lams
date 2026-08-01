from django.conf import settings


def session_timeout(request):
    """Exposes the session timeout to every template (in milliseconds,
    ready for JS) so the idle-warning toast's timing can never drift out
    of sync with the actual server-side SESSION_COOKIE_AGE setting."""
    return {"SESSION_TIMEOUT_MS": settings.SESSION_COOKIE_AGE * 1000}