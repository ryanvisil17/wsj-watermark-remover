#!/usr/bin/env python3
"""
WSJ PDF Processor - Remove headers and watermarks

This script processes Wall Street Journal PDFs to remove copyright
headers and watermarks that appear on each page. It handles both plain
text and hex-encoded watermarks embedded in the PDF structure.

The red header at the top is in plain text and can easily be striped
out. The large watermark is hex-encoded and needs a more subtle
approach, but identifying the strings initially was the most work.
After identifying them we can easily strip them out with regex and an
uncompressed version of the PDF.

Usage:
    python main.py input.pdf output.pdf

Process Overview:
    1. UNCOMPRESS - Use pdftk to uncompress the PDF structure
       - Makes the PDF content stream readable as plain text
       - Required for sed-based text manipulation in step 2
       - Example: Binary PDF → Uncompressed text-readable PDF

    2. REMOVE TEXT HEADERS - Use sed to strip plain text watermarks
       - Removes visible text strings like "For personal,"
       - Removes "non-commercial use only." and Dow Jones reprint info
       - These appear as literal strings in the uncompressed PDF content
       - Example: "For personal," → (removed)

    3. RE-COMPRESS - Use pdftk to compress the PDF back
       - Re-creates a valid PDF structure after sed manipulation
       - Required because sed may leave the PDF in an invalid state
       - Ensures qpdf can properly parse the PDF in step 4
       - Example: Modified uncompressed PDF → Valid compressed PDF

    4. UNPACK PDF STRUCTURE - Use qpdf to expand PDF objects
       - Converts compressed object streams to individual objects
       - Makes hex-encoded watermarks accessible for pattern matching
       - The --qdf flag creates a normalized "Quality PDF" structure
       - The --object-streams=disable flag expands all compressed streams
       - Required for reliable regex matching in step 5
       - Example: Compressed objects → Expanded individual objects

    5. REMOVE HEX WATERMARKS - Use pikepdf to strip encoded watermarks
       - Scans PDF content streams for hex-encoded text commands
       - Removes PDF graphics commands that draw watermark text
       - Watermarks are UTF-16BE encoded and embedded in PDF drawing ops
       - Pattern: q 0.000 0.000 0.502 rg BT <HEX> Tj ET Q
         * q = Save graphics state
         * 0.000 0.000 0.502 rg = Set dark blue color (RGB)
         * BT = Begin text object
         * <HEX> = Hex-encoded watermark text (UTF-16BE)
         * Tj = Show text operator
         * ET = End text object
         * Q = Restore graphics state
       - Example: q ... <0046...> ... Tj ET Q → (removed)

Dependencies:
    - pdftk: PDF manipulation (sudo apt install pdftk)
    - qpdf: PDF structure manipulation (sudo apt install qpdf)
    - sed: Stream editor (standard Unix tool)
    - pikepdf: Python PDF library (pip install pikepdf)
"""

import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pikepdf

HEADER = "For personal,|non-commercial use only.|Do not edit, alter or reproduce. For commercial reproduction or distribution, contact Dow Jones Reprints & Licensing at \\\\\\\\\\(800\\\\\\\\\\) 843-0008 or|www.djreprints.com"

# Hex-encoded "For personal," (UTF-16BE: 0x0046='F', 0x006f='o', 0x0072='r', ...)
HEX_FOR = b"<0046006f007200200070006500720073006f006e0061006c002c>"

# Hex-encoded " non-commercial use only." (UTF-16BE: 0x0020=' ', 0x006e='n', ...)
HEX_NONCOMM = b"<0020006e006f006e002d0063006f006d006d00650072006300690061006c00200075007300650020006f006e006c0079002e>"


def strip_watermark(stream_bytes: bytes) -> bytes:
    """
    Scans the PDF content stream for watermark drawing commands and
    removes them. Watermarks appear as PDF graphics state operations
    that draw text in a specific color (dark blue: RGB 0, 0, 0.502)
    with hex-encoded strings.

    Args:
        stream_bytes: Raw bytes from a PDF content stream

    Returns:
        Cleaned stream bytes with watermark commands removed
    """
    # Remove "For personal," watermark block
    stream_bytes = re.sub(
        rb"q\s+0\.000\s+0\.000\s+0\.502\s+rg\s+BT.*?"
        + re.escape(HEX_FOR)
        + rb".*?Tj\s+ET\s+Q\s*\r?\n",
        b"",
        stream_bytes,
    )

    # Remove " non-commercial use only." watermark block
    stream_bytes = re.sub(
        rb"q\s+0\.000\s+0\.000\s+0\.502\s+rg\s+BT.*?"
        + re.escape(HEX_NONCOMM)
        + rb".*?Tj\s+ET\s+Q\s*\r?\n",
        b"",
        stream_bytes,
    )

    return stream_bytes


def process_pdf(input_path: Path, output_path: Path):
    """
    This is the main processing pipeline that orchestrates the
    five-step cleaning process. All intermediate files are stored in a
    temporary directory that is automatically cleaned up when
    processing completes.

    Args:
        input_path: Path to the input WSJ PDF with watermarks
        output_path: Path where the cleaned PDF should be saved

    Raises:
        subprocess.CalledProcessError: If pdftk, sed, or qpdf commands fail
        pikepdf.PdfError: If PDF structure is invalid or unreadable
        FileNotFoundError: If input_path doesn't exist
    """

    with TemporaryDirectory() as work_dir:
        work_dir = Path(work_dir)

        # Step 1: Uncompress PDF
        print(f"[1/4] Uncompressing: {input_path.name}")
        uncompressed = work_dir / "uncompressed.pdf"
        subprocess.run(
            [
                "pdftk",
                str(input_path),
                "output",
                str(uncompressed),
                "uncompress",
            ],
            check=True,
            capture_output=True,
        )

        # Step 2: Remove text headers with sed
        print("[2/5] Removing text headers...")
        tmp_pdf = work_dir / "tmp.pdf"
        sed_cmd = f'sed -E -e "s/{HEADER}//g"'

        with open(uncompressed, "r") as f_in, open(tmp_pdf, "w") as f_out:
            subprocess.run(
                sed_cmd,
                shell=True,
                stdin=f_in,
                stdout=f_out,
                check=True,
            )

        # Step 3: Re-compress PDF (required for qpdf to work properly)
        print("[3/5] Re-compressing PDF...")
        no_header = work_dir / "no_header.pdf"
        subprocess.run(
            [
                "pdftk",
                str(tmp_pdf),
                "output",
                str(no_header),
                "compress",
            ],
            check=True,
            capture_output=True,
        )

        # Step 4: Unpack PDF for watermark removal
        print("[4/5] Unpacking PDF structure...")
        unpacked = work_dir / "unpacked.pdf"
        subprocess.run(
            [
                "qpdf",
                "--qdf",
                "--object-streams=disable",
                str(no_header),
                str(unpacked),
            ],
            check=True,
            capture_output=True,
        )

        # Step 5: Remove hex-encoded watermarks
        print("[5/5] Removing hex watermarks...")
        with pikepdf.open(unpacked) as pdf:
            pages_modified = 0

            for page in pdf.pages:
                contents = page.Contents
                if not contents:
                    continue

                streams = (
                    contents
                    if isinstance(contents, pikepdf.Array)
                    else [contents]
                )

                for stream in streams:
                    data = stream.read_bytes()
                    cleaned = strip_watermark(data)
                    if cleaned != data:
                        stream.write(cleaned)
                        pages_modified += 1

            pdf.save(output_path)

        print(
            f"Complete: {output_path.name} ({pages_modified} pages modified)"
        )


def main():
    """
    Validates command-line arguments, checks input file exists, and
    runs the PDF processing pipeline.

    Exit codes:
        0: Success
        1: Error (invalid arguments, file not found, or processing
            failed)
    """
    if len(sys.argv) != 3:
        print("Usage: python main.py input.pdf output.pdf")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    try:
        process_pdf(input_path, output_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
