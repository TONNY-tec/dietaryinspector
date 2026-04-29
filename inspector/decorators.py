from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def premium_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.userprofile.has_active_premium():
            return view_func(request, *args, **kwargs)
        else:
            messages.warning(request, "This is a premium feature. Please upgrade your account.")
            return redirect('pricing') # Redirect to your upgrade page
    return _wrapped_view