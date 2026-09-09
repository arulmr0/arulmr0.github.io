import os
from unittest import mock

import jwt

from app.core.config import DEV_SECRET_KEY, Settings
from app.main import harden_secret_key


def test_dev_secret_is_replaced_at_startup():
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HFS_SECRET_KEY", None)
        settings = Settings(_env_file=None)
    assert settings.secret_key == DEV_SECRET_KEY
    assert harden_secret_key(settings) is True
    assert settings.secret_key != DEV_SECRET_KEY
    assert len(settings.secret_key) >= 32
    # tokens signed with the new key verify, tokens signed with the old key do not
    token = jwt.encode({"sub": "1"}, settings.secret_key, algorithm="HS256")
    assert jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"] == "1"


def test_explicit_secret_is_kept():
    settings = Settings(_env_file=None, secret_key="x" * 40)
    assert harden_secret_key(settings) is False
    assert settings.secret_key == "x" * 40


def test_seed_on_start_seeds_once(monkeypatch, capsys):
    from app import main as main_module

    calls: list[str] = []
    monkeypatch.setattr("app.seed.seed", lambda db: calls.append("seeded"))
    main_module.seed_if_requested(Settings(_env_file=None, seed_on_start=False))
    assert calls == []
    main_module.seed_if_requested(Settings(_env_file=None, seed_on_start=True))
    assert calls == ["seeded"]
