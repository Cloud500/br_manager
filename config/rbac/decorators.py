from functools import wraps
from django.http import HttpResponseForbidden

from apps.committees.models import Committee
from config.rbac.services import has_permission


def permission_required(permission_key, committee_kwarg="committee_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            committee_id = kwargs.get(committee_kwarg)
            committee = Committee.objects.get(id=committee_id)

            if not has_permission(request.user, permission_key, committee, ):
                return HttpResponseForbidden()

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
