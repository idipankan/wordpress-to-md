# WordPress → Markdown Converter

A Streamlit app that converts WordPress WXR XML exports into clean, individual Markdown files — ready for [Bear Blog](https://bearblog.dev), Hugo, Jekyll, or any static-site generator.

## Features

- **Upload & convert** — drag-and-drop your WordPress export XML
- **Flexible filters** — choose post types (posts, pages) and statuses (published, draft, private, pending)
- **Output options** — toggle date-prefixed filenames (`YYYYMMDD-slug.md`) and choose between YAML front-matter or inline headings
- **Preview** — inspect converted files before downloading
- **One-click ZIP download** — grab all your Markdown files in a single archive
- **Preserves embeds** — iframes (YouTube, Datawrapper, etc.) and adjacent scripts are kept intact
- **Auto-detects WP namespace** — works with export versions 1.0, 1.1, and 1.2

## Quick Start

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

## CLI Usage

You can also use the converter directly from the command line:

```bash
python convert.py export.xml -o output_dir
```

| Flag | Description |
|---|---|
| `-o`, `--output` | Output directory (default: `posts`) |
| `--types` | Post types to include (default: `post`) |
| `--statuses` | Statuses to include (default: `publish`) |
| `--no-date-prefix` | Omit the `YYYYMMDD-` date prefix |
| `--yaml` | Use YAML front-matter instead of inline heading |

**Examples:**

```bash
# Export only published posts (default)
python convert.py WordPress.xml

# Export posts and pages, including drafts
python convert.py WordPress.xml --types post page --statuses publish draft

# No date prefix, YAML front-matter
python convert.py WordPress.xml --no-date-prefix --yaml
```

## How to Get Your WordPress Export

1. Go to your WordPress Admin dashboard
2. Navigate to **Tools → Export**
3. Select **All content** (or just Posts/Pages)
4. Click **Download Export File**
5. Upload the resulting `.xml` file into the app

## Project Structure

```
wp-to-bear/
├── app.py              # Streamlit web app
├── convert.py          # Core conversion library + CLI
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md
```

## License

MIT
