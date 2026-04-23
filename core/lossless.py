import pikepdf


def compress_lossless(input_path: str, output_path: str, level: int = 9) -> None:
    """pikepdf 無失真壓縮：壓縮串流並生成物件流。

    pikepdf 9+ 移除了 flate_level / recompress_flate，
    改以 compress_streams + object_stream_mode 達到最佳壓縮。
    level 參數保留供呼叫端傳入，但在此版本中不影響 pikepdf 行為。
    """
    with pikepdf.Pdf.open(input_path) as pdf:
        pdf.save(
            output_path,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
