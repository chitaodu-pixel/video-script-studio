from video_script_studio.services.preview_audio import PreviewAudioStore


def test_clear_only_deletes_files_inside_preview_folder(tmp_path) -> None:
    store = PreviewAudioStore()
    preview = store.directory(tmp_path)
    preview.mkdir(parents=True)
    (preview / "one.mp3").write_bytes(b"one")
    (preview / "two.wav").write_bytes(b"two")
    nested = preview / "keep-folder"
    nested.mkdir()
    outside = tmp_path / "saved.mp3"
    outside.write_bytes(b"saved")

    assert store.clear(tmp_path) == 2
    assert store.files(tmp_path) == []
    assert nested.exists()
    assert outside.read_bytes() == b"saved"
