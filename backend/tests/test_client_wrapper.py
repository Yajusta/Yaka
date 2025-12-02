"""Custom TestClient wrapper to work around httpx compatibility issue."""

from typing import Any, Dict, Literal, Optional

from starlette.testclient import TestClient as StarletteTestClient


class TestClient:
    """Custom TestClient wrapper that works around httpx compatibility issues."""

    def __init__(
        self,
        app,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: Literal["asyncio", "trio"] = "asyncio",
        backend_options: Optional[Dict[str, Any]] = None,
        cookies: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ):

        # Create the underlying Starlette TestClient but avoid the problematic super().__init__
        self._app = app
        self._base_url = base_url
        self._raise_server_exceptions = raise_server_exceptions
        self._root_path = root_path
        self._backend = backend
        self._backend_options = backend_options or {}
        self._cookies = cookies
        self._headers = headers or {}

        # Create a TestClient instance with a modified approach
        self._client = StarletteTestClient(
            app=app,
            base_url=base_url,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            backend=backend,
            backend_options=backend_options,
            cookies=cookies,
            headers=headers,
        )

        # Copy all the methods from the underlying client
        for method_name in ["get", "post", "put", "patch", "delete", "head", "options"]:
            if hasattr(self._client, method_name):
                setattr(self, method_name, getattr(self._client, method_name))

    def __enter__(self):
        return self._client.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._client.__exit__(exc_type, exc_val, exc_tb)
