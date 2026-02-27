import importlib
import os
import sys


def test_main_import_without_static_dirs() -> None:
    original_jwt_secret = os.environ.get("JWT_SECRET_KEY")
    os.environ["JWT_SECRET_KEY"] = "test-secret"

    try:
        sys.modules.pop("main", None)
        module = importlib.import_module("main")
        assert hasattr(module, "app")
    finally:
        sys.modules.pop("main", None)
        if original_jwt_secret is None:
            os.environ.pop("JWT_SECRET_KEY", None)
        else:
            os.environ["JWT_SECRET_KEY"] = original_jwt_secret
