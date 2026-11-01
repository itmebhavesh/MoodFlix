"""Small in-memory helpers: rate limiting and same-origin write protection."""
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from urllib.parse import urlparse

from flask import current_app, jsonify, request

_hits = defaultdict(deque)
_lock = threading.Lock()


def rate_limit(limit, window_seconds):
    """Allow `limit` calls per `window_seconds` for each client IP and endpoint."""
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if current_app.config.get("RATELIMIT_DISABLED") or current_app.testing:
                return function(*args, **kwargs)
            key = (function.__name__, request.remote_addr)
            now = time.monotonic()
            with _lock:
                queue = _hits[key]
                while queue and now - queue[0] > window_seconds:
                    queue.popleft()
                if len(queue) >= limit:
                    retry = int(window_seconds - (now - queue[0])) + 1
                    response = jsonify({"error": "Too many attempts. Please try again later."})
                    response.status_code = 429
                    response.headers["Retry-After"] = str(retry)
                    return response
                queue.append(now)
            return function(*args, **kwargs)
        return wrapped
    return decorator


def install_origin_check(app):
    """Reject browser write requests that come from another website."""
    @app.before_request
    def block_cross_origin_writes():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            if origin and urlparse(origin).netloc != request.host:
                return jsonify({"error": "Cross-origin request blocked."}), 403