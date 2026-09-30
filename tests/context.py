def extra_context(request):
    """More context for the project template, trying to override a variable of its own in vain."""
    return {"team": f"team of {request.user.get_username()}", "username": "overridden"}
