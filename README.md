# WSJ Watermark Remover

Remove copyright headers and watermarks from Wall Street Journal PDFs.

---

## Docker Usage

### Linux / macOS

```bash
docker run --rm -u "$(id -u)":"$(id -g)" -v ./:/workspace \
  ryanvisil17/wsj-watermark-remover:latest input.pdf output.pdf
```

### Windows

```powershell
docker run --rm -v ${PWD}:/workspace \
  ryanvisil17/wsj-watermark-remover:latest input.pdf output.pdf
```

---

## Local Installation

### Linux

**Install Dependencies:**

```bash
sudo apt update
sudo apt install pdftk qpdf

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python package
pip install pikepdf
```

**Usage:**

```bash
python main.py input.pdf output.pdf
```

---

### Windows

**Install Dependencies:**

1. **PDFtk Server**: Download from https://www.pdflabs.com/tools/pdftk-server/
2. **QPDF**: Install using winget or download from https://github.com/qpdf/qpdf/releases
3. **pikepdf**: Install via pip (see below)

**Installing QPDF:**

```powershell
# Using winget (recommended)
winget install -e --id QPDF.QPDF

# Restart PowerShell, then verify
qpdf --version
```

**If QPDF is not in PATH:**

1. Press `Win + R`, type `sysdm.cpl`
2. Advanced → Environment Variables → System Variables
3. Find `PATH`, click Edit
4. Add: `C:\Program Files\qpdf\bin` (check actual version, e.g., `C:\Program Files\qpdf 12.2.0\bin`)
5. Click OK, restart PowerShell

**Setup Python Environment:**

```powershell
python -m venv venv
.\venv\Scripts\activate

pip install pikepdf
```

**Usage:**

```powershell
python main_windows.py input.pdf output.pdf
```

---

## How It Works

The tool removes watermarks in 5 steps:

1. **Uncompress** - Decompresses PDF structure with `pdftk`
2. **Remove text** - Strips plain text headers using `sed` (Linux) or Python (Windows)
3. **Recompress** - Rebuilds valid PDF structure with `pdftk`
4. **Unpack** - Expands PDF objects with `qpdf`
5. **Remove hex** - Strips hex-encoded watermarks with `pikepdf`

---

## Troubleshooting

**Windows: 'pdftk' or 'qpdf' not recognized**

- Ensure tools are installed and added to PATH
- Restart PowerShell after installation

**Docker: Permission errors (Linux)**

- Use `-u "$(id -u)":"$(id -g)"` flag to match file ownership

---

## License

MIT License - For personal, educational use only.
