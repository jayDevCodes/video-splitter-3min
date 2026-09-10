from app.services.file_manager import safe_stem
from app.services.video_splitter import OUTPUT_SIZES


def test_safe_stem_removes_unsafe_characters():
    assert safe_stem("my video: final?.mp4") == "my_video_final"
    assert safe_stem("...mp4") == "video"


def test_output_sizes_are_youtube_friendly():
    assert OUTPUT_SIZES["vertical"] == (1080, 1920)
    assert OUTPUT_SIZES["horizontal"] == (1920, 1080)
