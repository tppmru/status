"""Проверяет публичные URL без учётных данных и записи истории."""

import json
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BODY = 2 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class FrontendDocument(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_app = False
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag == "div" and ("id", "app") in attrs:
            self.has_app = True

    def handle_data(self, data):
        if self.in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False


def is_frontend(body):
    page = FrontendDocument()
    page.feed(body.decode("utf-8"))
    return page.has_app and page.title.strip() == "Технополис бот поддержки"


def is_backend(body):
    document = json.loads(body)
    if not isinstance(document, dict) or not isinstance(document.get("openapi"), str):
        return False
    paths = document.get("paths")
    return bool(document["openapi"]) and isinstance(paths, dict) and isinstance(paths.get("/api/statuses"), dict)


def check(name, url, valid):
    opener = build_opener(NoRedirect)
    request = Request(url, headers={"User-Agent": "tppmru-status"})
    try:
        with opener.open(request, timeout=10) as response:
            body = response.read(MAX_BODY + 1)
            ok = response.status == 200 and len(body) <= MAX_BODY and valid(body)
            result = "маркеры совпали" if ok else "ответ не соответствует проверке"
            print(f"{name}: HTTP {response.status}, {result}")
            return ok
    except HTTPError as error:
        print(f"{name}: HTTP {error.code}")
    except ValueError:
        print(f"{name}: неожиданный формат ответа")
    except (OSError, HTTPException) as error:
        print(f"{name}: ошибка соединения ({type(error).__name__})")
    return False


if __name__ == "__main__":
    checks = [
        check("Frontend", "https://tma.tppm.ru/", is_frontend),
        check("Backend", "https://tma.tppm.ru/api/docs/openapi.json", is_backend),
    ]
    raise SystemExit(0 if all(checks) else 1)
