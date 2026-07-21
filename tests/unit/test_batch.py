from PIL import Image

from photo_border.core.batch import process_batch
from photo_border.core.models import BorderConfig, BorderMode


def _make_jpeg(path, size=(20, 20), color=(1, 2, 3)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


class TestProcessBatchFlat:
    def test_processes_only_supported_files_in_top_level(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        _make_jpeg(input_dir / "a.jpg")
        _make_jpeg(input_dir / "b.png")
        (input_dir / "notes.txt").parent.mkdir(parents=True, exist_ok=True)
        (input_dir / "notes.txt").write_text("hello")

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        report = process_batch(input_dir, output_dir, config)

        assert report.total == 2
        assert report.succeeded == 2
        assert report.failed == 0
        assert (output_dir / "a.jpg").exists()
        assert (output_dir / "b.png").exists()

    def test_ignores_subdirectory_when_not_recursive(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        _make_jpeg(input_dir / "top.jpg")
        _make_jpeg(input_dir / "sub" / "nested.jpg")

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        report = process_batch(input_dir, output_dir, config, recursive=False)

        assert report.total == 1
        assert (output_dir / "top.jpg").exists()
        assert not (output_dir / "sub" / "nested.jpg").exists()


class TestProcessBatchRecursive:
    def test_recursive_preserves_subfolder_structure(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        _make_jpeg(input_dir / "top.jpg")
        _make_jpeg(input_dir / "sub" / "nested.jpg")

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        report = process_batch(input_dir, output_dir, config, recursive=True)

        assert report.total == 2
        assert (output_dir / "top.jpg").exists()
        assert (output_dir / "sub" / "nested.jpg").exists()


class TestProcessBatchErrorIsolation:
    def test_corrupted_file_does_not_stop_the_batch(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        input_dir.mkdir(parents=True)
        _make_jpeg(input_dir / "good1.jpg")
        (input_dir / "broken.jpg").write_bytes(b"not-a-real-image")
        _make_jpeg(input_dir / "good2.jpg")

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        report = process_batch(input_dir, output_dir, config)

        assert report.total == 3
        assert report.succeeded == 2
        assert report.failed == 1
        failed_results = [r for r in report.results if not r.success]
        assert len(failed_results) == 1
        assert failed_results[0].error is not None


class TestProcessBatchOutputFormat:
    def test_changes_extension_when_output_format_set(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        _make_jpeg(input_dir / "a.jpg")

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, output_format="png")
        report = process_batch(input_dir, output_dir, config)

        assert report.succeeded == 1
        assert (output_dir / "a.png").exists()
        assert not (output_dir / "a.jpg").exists()


class TestProcessBatchOverwrite:
    def test_skips_existing_output_when_overwrite_false(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        _make_jpeg(input_dir / "a.jpg", color=(1, 2, 3))
        _make_jpeg(input_dir / "b.jpg", color=(4, 5, 6))
        _make_jpeg(output_dir / "a.jpg", color=(9, 9, 9))  # 既有輸出

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        report = process_batch(input_dir, output_dir, config, overwrite=False)

        assert report.total == 1  # 只處理 b.jpg
        assert report.succeeded == 1
        with Image.open(output_dir / "a.jpg") as untouched:
            assert untouched.getpixel((0, 0)) == (9, 9, 9)

    def test_overwrite_true_by_default(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        _make_jpeg(input_dir / "a.jpg", color=(1, 2, 3))
        _make_jpeg(output_dir / "a.jpg", color=(9, 9, 9))

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        report = process_batch(input_dir, output_dir, config)

        assert report.total == 1
        with Image.open(output_dir / "a.jpg") as overwritten:
            assert overwritten.getpixel((0, 0)) != (9, 9, 9)


class TestProcessBatchProgressCallback:
    def test_progress_cb_called_once_per_file_with_correct_totals(self, tmp_path):
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"
        _make_jpeg(input_dir / "a.jpg")
        _make_jpeg(input_dir / "b.jpg")
        _make_jpeg(input_dir / "c.jpg")

        calls = []

        def on_progress(index, total, result):
            calls.append((index, total, result.success))

        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        process_batch(input_dir, output_dir, config, progress_cb=on_progress)

        assert calls == [(1, 3, True), (2, 3, True), (3, 3, True)]
