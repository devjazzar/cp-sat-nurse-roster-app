from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest
from django.urls import path, re_path

from config.api import api


def spa(request: HttpRequest, path: str = "") -> FileResponse:
    """Every path that is neither the API nor a file of the SPA is a client-side route."""
    index = settings.SPA_DIR / "index.html"
    if not index.is_file():
        raise Http404("the SPA is not built here; in development Vite serves it")
    return FileResponse(index.open("rb"), content_type="text/html")


urlpatterns = [
    path("api/", api.urls),
    re_path(r"^(?!api/)(?P<path>.*)$", spa),
]
