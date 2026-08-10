from video_script_studio.services.credential_store import AzureCredentialStore


def test_credential_store_round_trip(tmp_path, monkeypatch) -> None:
    store = AzureCredentialStore(tmp_path / "settings.json")
    monkeypatch.setattr(store, "protect", lambda value: f"encrypted:{value}")
    monkeypatch.setattr(store, "unprotect", lambda value: value.removeprefix("encrypted:"))

    store.save("secret", "eastasia")

    assert store.load() == ("secret", "eastasia")
    assert "secret" not in store.path.read_text(encoding="utf-8").replace("encrypted:secret", "")
    store.clear()
    assert store.load() is None
