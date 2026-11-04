from django.test import Client


def test_client_side_routes_get_the_spa(settings, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>SPA</title>")
    settings.SPA_DIR = tmp_path

    r = Client().get("/some/client/route")

    assert r.status_code == 200 and b"<title>SPA</title>" in b"".join(r.streaming_content)


def test_unknown_api_paths_are_not_the_spa(settings, tmp_path):
    (tmp_path / "index.html").write_text("spa")
    settings.SPA_DIR = tmp_path

    assert Client().get("/api/nope").status_code == 404


def test_a_missing_build_is_a_404_not_a_crash(settings, tmp_path):
    settings.SPA_DIR = tmp_path

    assert Client().get("/").status_code == 404
