import functools
import json

from django.http import JsonResponse

from common.exceptions import HealthPulseException


def json_endpoint(view_func):
    """
    Wrap an AJAX view so that:
      - HealthPulseException -> {"ok": False, "error": "..."} with HTTP 400
      - any other exception   -> {"ok": False, "error": "..."} with HTTP 500
      - request.json is populated from the JSON body when present
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.body:
            try:
                request.json = json.loads(request.body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                request.json = {}
        else:
            request.json = {}
        try:
            return view_func(request, *args, **kwargs)
        except HealthPulseException as exc:
            return JsonResponse({"ok": False, "error": exc.message}, status=400)
        except Exception as exc:  # pragma: no cover - safety net
            return JsonResponse({"ok": False, "error": f"Unexpected error: {exc}"}, status=500)

    return wrapper
