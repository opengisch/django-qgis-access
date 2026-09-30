from django.http import HttpResponse


def username(user):
    return user.get_username() if user.is_authenticated else "anonymous"


def whoami(request):
    """The name of the user of the request, for GET and for POST, which the CSRF check guards."""
    return HttpResponse(username(request.user))


async def async_whoami(request):
    return HttpResponse(username(await request.auser()))
