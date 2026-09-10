from app.services.file_manager import safe_stem


def test_safe_stem_removes_unsafe_characters():
    assert safe_stem("my video: final?.mp4") == "my_video_final"
    assert safe_stem("...mp4") == "video"
