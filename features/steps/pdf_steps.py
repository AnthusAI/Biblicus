from __future__ import annotations

from pathlib import Path

from behave import given


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _minimal_single_page_pdf_bytes(*, text: str) -> bytes:
    escaped_text = _escape_pdf_text(text)
    content_stream = f"BT /F1 24 Tf 72 720 Td ({escaped_text}) Tj ET\n"
    content_bytes = content_stream.encode("ascii")

    objects: list[bytes] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        b"<< /Length "
        + str(len(content_bytes)).encode("ascii")
        + b" >>\nstream\n"
        + content_bytes
        + b"endstream"
    )

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body_parts: list[bytes] = [header]

    offsets: list[int] = [0]
    current_offset = len(header)
    for index, obj in enumerate(objects, start=1):
        offsets.append(current_offset)
        obj_bytes = f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
        body_parts.append(obj_bytes)
        current_offset += len(obj_bytes)

    xref_start = current_offset
    xref_lines: list[bytes] = []
    xref_lines.append(b"xref\n")
    xref_lines.append(f"0 {len(objects) + 1}\n".encode("ascii"))
    xref_lines.append(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
        + b"startxref\n"
        + f"{xref_start}\n".encode("ascii")
        + b"%%EOF\n"
    )

    return b"".join(body_parts + xref_lines + [trailer])


def _minimal_single_page_pdf_bytes_with_no_text() -> bytes:
    objects: list[bytes] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length 0 >>\nstream\nendstream")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body_parts: list[bytes] = [header]

    offsets: list[int] = [0]
    current_offset = len(header)
    for index, obj in enumerate(objects, start=1):
        offsets.append(current_offset)
        obj_bytes = f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
        body_parts.append(obj_bytes)
        current_offset += len(obj_bytes)

    xref_start = current_offset
    xref_lines: list[bytes] = []
    xref_lines.append(b"xref\n")
    xref_lines.append(f"0 {len(objects) + 1}\n".encode("ascii"))
    xref_lines.append(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
        + b"startxref\n"
        + f"{xref_start}\n".encode("ascii")
        + b"%%EOF\n"
    )

    return b"".join(body_parts + xref_lines + [trailer])


@given('a Portable Document Format file "{filename}" exists with text "{text}"')
def step_pdf_file_exists_with_text(context, filename: str, text: str) -> None:
    path = Path(context.workdir) / filename
    path.write_bytes(_minimal_single_page_pdf_bytes(text=text))


@given('a Portable Document Format file "{filename}" exists with no extractable text')
def step_pdf_file_exists_with_no_text(context, filename: str) -> None:
    path = Path(context.workdir) / filename
    path.write_bytes(_minimal_single_page_pdf_bytes_with_no_text())
