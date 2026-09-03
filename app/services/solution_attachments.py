"""Conversion of uploaded solution attachments to LLM-compatible images."""

import base64
import binascii
from io import BytesIO

from PIL import Image
from PIL import ImageOps
from pillow_heif import register_heif_opener


MAX_SOLUTION_IMAGE_DIMENSION = 1080
JPEG_QUALITY = 75


register_heif_opener(thumbnails=False)


def convert_heic_data_url_to_jpeg(data_url):
    """Decode a HEIC/HEIF data URL and return a compressed JPEG data URL."""

    header, separator, payload = data_url.partition(",")

    if not separator or ";base64" not in header.lower():
        raise ValueError("HEIC attachment must be a base64 data URL")

    try:
        raw_image = base64.b64decode(
            "".join(payload.split()),
            validate=True,
        )

        with Image.open(BytesIO(raw_image)) as source_image:
            image = ImageOps.exif_transpose(source_image).convert("RGB")
            image.thumbnail(
                (
                    MAX_SOLUTION_IMAGE_DIMENSION,
                    MAX_SOLUTION_IMAGE_DIMENSION,
                ),
                Image.Resampling.LANCZOS,
            )

            output = BytesIO()
            image.save(
                output,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
            )

    except (
        Image.DecompressionBombError,
        binascii.Error,
        OSError,
        SyntaxError,
        ValueError,
    ) as error:
        raise ValueError("HEIC attachment could not be decoded") from error

    encoded = base64.b64encode(output.getvalue()).decode("ascii")

    return "data:image/jpeg;base64," + encoded
