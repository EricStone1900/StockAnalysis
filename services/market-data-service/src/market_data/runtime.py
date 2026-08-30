import os
import socket
from pathlib import Path
from urllib.parse import urlparse


def environment_secret(name: str, default: str) -> str:
    """优先读取 Docker secret（`NAME_FILE`），本地开发回退到环境变量。"""
    secret_file = os.getenv(f"{name}_FILE")
    if secret_file:
        return Path(secret_file).read_text().strip()
    return os.getenv(name, default)


def endpoint_reachable(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname
    if host is None:
        return False
    default_ports = {"http": 80, "https": 443, "nats": 4222, "postgresql": 5432}
    port = parsed.port or default_ports.get(parsed.scheme)
    if port is None:
        return False
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False
