"""Thin HTTP client for the simulator with retries on transport errors and 5xx."""
from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger("controller.api")


class SimError(Exception):
    def __init__(self, status: int, code: str, detail):
        super().__init__(f"{status} {code}: {detail}")
        self.status, self.code, self.detail = status, code, detail


class Sim:
    def __init__(self, url: str, retries: int = 8):
        self.c = httpx.Client(base_url=url.rstrip("/"), timeout=300)
        self.retries = retries

    def _req(self, method: str, path: str, **kw):
        delay = 0.5
        for attempt in range(self.retries):
            try:
                r = self.c.request(method, path, **kw)
            except httpx.TransportError as e:
                log.warning("transport error on %s %s: %s (retry %d)", method, path, e, attempt)
                time.sleep(delay)
                delay = min(delay * 2, 10)
                continue
            if r.status_code >= 500:
                log.warning("%s on %s %s (retry %d)", r.status_code, method, path, attempt)
                time.sleep(delay)
                delay = min(delay * 2, 10)
                continue
            if r.status_code >= 400:
                try:
                    body = r.json()
                except ValueError:
                    body = {"error": "http_error", "detail": r.text}
                raise SimError(r.status_code, body.get("error", "http_error"), body.get("detail"))
            return r
        raise SimError(599, "unreachable", f"{method} {path} failed after {self.retries} retries")

    def get(self, path, **kw):
        return self._req("GET", path, **kw).json()

    def post(self, path, body):
        return self._req("POST", path, json=body).json()

    def put(self, path, body):
        return self._req("PUT", path, json=body).json()

    def text(self, path) -> str:
        return self._req("GET", path).text

    def wait_ready(self, timeout_s: float = 600):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            try:
                if self.c.get("/health").status_code == 200:
                    return
            except httpx.TransportError:
                pass
            time.sleep(1)
        raise SimError(599, "unreachable", "simulator not ready")
