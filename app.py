"""
WordPress → Markdown Converter
A Streamlit app to convert WordPress WXR XML exports to individual Markdown files.
"""

import io
import zipfile

import streamlit as st
from convert import parse_wordpress_xml, generate_markdown_files


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="WP → Markdown Converter",
    page_icon="📝",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS for a premium look
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hero header */
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .hero h1 {
        margin: 0 0 0.5rem 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .hero p {
        margin: 0;
        font-size: 1.05rem;
        opacity: 0.92;
    }

    /* Stat cards */
    .stat-row {
        display: flex;
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .stat-card {
        flex: 1;
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f0 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .stat-card .number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    .stat-card .label {
        font-size: 0.85rem;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Dark mode overrides */
    @media (prefers-color-scheme: dark) {
        .stat-card {
            background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3d 100%);
        }
        .stat-card .label { color: #aaa; }
    }

    /* File preview cards */
    .preview-card {
        border: 1px solid rgba(102, 126, 234, 0.25);
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        background: rgba(102, 126, 234, 0.04);
        transition: box-shadow 0.2s;
    }
    .preview-card:hover {
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.15);
    }
    .preview-card .fname {
        font-weight: 600;
        font-size: 0.92rem;
        color: #667eea;
        margin-bottom: 0.4rem;
    }
    .preview-card .snippet {
        font-size: 0.82rem;
        color: #666;
        line-height: 1.45;
        white-space: pre-wrap;
    }

    /* Download button area */
    .download-area {
        text-align: center;
        margin: 2rem 0;
    }

    /* Sidebar tweaks */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fc 0%, #eef1f8 100%);
    }
    @media (prefers-color-scheme: dark) {
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="hero">
    <h1>📝 WordPress → Markdown Converter</h1>
    <p>Upload your WordPress export XML and download clean Markdown files — ready for Bear Blog, Hugo, Jekyll, or any static-site generator.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — options
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Options")

    st.subheader("Content Filters")
    inc_posts = st.checkbox("Posts", value=True)
    inc_pages = st.checkbox("Pages", value=False)

    st.subheader("Statuses")
    inc_publish = st.checkbox("Published", value=True)
    inc_draft = st.checkbox("Draft", value=False)
    inc_private = st.checkbox("Private", value=False)
    inc_pending = st.checkbox("Pending", value=False)

    st.divider()

    st.subheader("Output Format")
    date_prefix = st.toggle("Date prefix on filenames", value=True,
                            help="Prepend YYYYMMDD- to each filename.")
    yaml_fm = st.toggle("YAML front-matter", value=False,
                        help="Use a YAML --- block instead of an inline # heading.")

# Build filter sets from sidebar state
selected_types: set[str] = set()
if inc_posts:
    selected_types.add("post")
if inc_pages:
    selected_types.add("page")

selected_statuses: set[str] = set()
if inc_publish:
    selected_statuses.add("publish")
if inc_draft:
    selected_statuses.add("draft")
if inc_private:
    selected_statuses.add("private")
if inc_pending:
    selected_statuses.add("pending")

# ---------------------------------------------------------------------------
# File uploader
# ---------------------------------------------------------------------------

uploaded = st.file_uploader(
    "Upload your WordPress export (.xml)",
    type=["xml"],
    help="Go to WordPress Admin → Tools → Export to download the file.",
)

if not uploaded:
    st.info("👆 Upload a WordPress XML export to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# Guard: need at least one filter
# ---------------------------------------------------------------------------

if not selected_types:
    st.warning("Select at least one **content type** in the sidebar.")
    st.stop()
if not selected_statuses:
    st.warning("Select at least one **status** in the sidebar.")
    st.stop()

# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------

with st.spinner("Parsing XML…"):
    posts = parse_wordpress_xml(
        io.BytesIO(uploaded.getvalue()),
        post_types=selected_types,
        post_statuses=selected_statuses,
    )

if not posts:
    st.warning("No items matched your filters. Try adjusting the sidebar options.")
    st.stop()

files = generate_markdown_files(
    posts,
    date_prefix=date_prefix,
    yaml_frontmatter=yaml_fm,
)

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

type_counts = {}
for p in posts:
    type_counts[p['type']] = type_counts.get(p['type'], 0) + 1

status_counts = {}
for p in posts:
    status_counts[p['status']] = status_counts.get(p['status'], 0) + 1

cols = st.columns(len(type_counts) + len(status_counts) + 1)
cols[0].metric("Total Files", len(files))
idx = 1
for t, c in type_counts.items():
    cols[idx].metric(t.title() + "s", c)
    idx += 1
for s, c in status_counts.items():
    cols[idx].metric(s.title(), c)
    idx += 1

# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

st.subheader("📄 Preview")
preview_count = min(5, len(files))

for fname, content in files[:preview_count]:
    snippet = content[:500] + ("…" if len(content) > 500 else "")
    with st.expander(f"**{fname}**", expanded=False):
        st.code(snippet, language="markdown")

if len(files) > preview_count:
    st.caption(f"Showing {preview_count} of {len(files)} files. Download the ZIP for the full set.")

# ---------------------------------------------------------------------------
# ZIP download
# ---------------------------------------------------------------------------

zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
    for fname, content in files:
        zf.writestr(fname, content)
zip_buffer.seek(0)

st.divider()

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    st.download_button(
        label="⬇️  Download all as ZIP",
        data=zip_buffer,
        file_name="wordpress-markdown-export.zip",
        mime="application/zip",
        use_container_width=True,
        type="primary",
    )
