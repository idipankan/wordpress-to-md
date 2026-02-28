"""
WordPress XML to Markdown converter.

Generic converter that works with any standard WordPress WXR export.
Can be used as a library (imported by the Streamlit app) or standalone via CLI.
"""

import xml.etree.ElementTree as ET
import html
import re
import os
from datetime import datetime


# ---------------------------------------------------------------------------
# HTML → Markdown
# ---------------------------------------------------------------------------

def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to Markdown format."""
    if not html_content:
        return ""

    content = html.unescape(html_content)

    # Remove CDATA wrappers
    content = content.replace('<![CDATA[', '').replace(']]>', '')

    # --- Block-level elements ---

    # Headings
    for level in range(1, 7):
        tag = f"h{level}"
        prefix = "#" * level
        content = re.sub(
            rf'<{tag}[^>]*>(.*?)</{tag}>',
            rf'{prefix} \1',
            content,
            flags=re.DOTALL,
        )

    # Blockquotes
    def _convert_blockquote(m):
        inner = m.group(1).strip().replace('\n', '\n> ')
        return f'\n> {inner}\n'
    content = re.sub(
        r'<blockquote[^>]*>(.*?)</blockquote>',
        _convert_blockquote,
        content,
        flags=re.DOTALL,
    )

    # Ordered lists
    def _convert_ol(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), flags=re.DOTALL)
        return '\n' + '\n'.join(f'{i+1}. {item.strip()}' for i, item in enumerate(items)) + '\n'
    content = re.sub(r'<ol[^>]*>(.*?)</ol>', _convert_ol, content, flags=re.DOTALL)

    # Unordered lists
    def _convert_ul(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), flags=re.DOTALL)
        return '\n' + '\n'.join(f'- {item.strip()}' for item in items) + '\n'
    content = re.sub(r'<ul[^>]*>(.*?)</ul>', _convert_ul, content, flags=re.DOTALL)

    # --- Inline elements ---

    # Bold
    content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
    content = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', content, flags=re.DOTALL)

    # Italic
    content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
    content = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', content, flags=re.DOTALL)

    # Links
    content = re.sub(
        r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        r'[\2](\1)',
        content,
        flags=re.DOTALL,
    )

    # Images (with and without alt text)
    content = re.sub(
        r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/?>',
        r'![\2](\1)',
        content,
    )
    content = re.sub(
        r'<img[^>]*src=["\']([^"\']*)["\'][^>]*/?>',
        r'![](\1)',
        content,
    )

    # Line breaks
    content = re.sub(r'<br\s*/?>', '\n', content)

    # Paragraphs
    content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', content, flags=re.DOTALL)

    # --- Preserve embedded elements ---

    # Iframes (YouTube, Datawrapper, etc.)
    iframes: list[str] = []
    def _save_iframe(m):
        iframes.append(m.group(0))
        return f'___IFRAME_{len(iframes)-1}___'
    content = re.sub(
        r'<iframe[^>]*>.*?</iframe>',
        _save_iframe,
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Scripts adjacent to embeds
    scripts: list[str] = []
    def _save_script(m):
        scripts.append(m.group(0))
        return f'___SCRIPT_{len(scripts)-1}___'
    content = re.sub(
        r'<script[^>]*>.*?</script>',
        _save_script,
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Strip remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)

    # Restore preserved elements
    for i, iframe in enumerate(iframes):
        content = content.replace(f'___IFRAME_{i}___', f'\n\n{iframe}\n\n')
    for i, script in enumerate(scripts):
        content = content.replace(f'___SCRIPT_{i}___', f'\n\n{script}\n\n')

    # --- Clean up whitespace & residual entities ---
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.replace('&nbsp;', ' ')
    content = content.replace('&amp;', '&')
    content = content.replace('&quot;', '"')
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')

    return content.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_filename(title: str) -> str:
    """Convert a title to a safe filename slug."""
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def _detect_wp_namespace(root: ET.Element) -> dict[str, str]:
    """
    Auto-detect WP export namespace version from the XML root element.
    Falls back to 1.2 if detection fails.
    """
    # Scan all namespace declarations on the root
    ns_map: dict[str, str] = {}
    for attr, value in root.attrib.items():
        if attr.startswith('{') or '/' in value:
            continue

    # Try to find the wp namespace from the raw XML or element tags
    wp_ns = ''
    content_ns = 'http://purl.org/rss/1.0/modules/content/'
    dc_ns = 'http://purl.org/dc/elements/1.1/'

    # Walk the tree to discover namespaces actually used
    for elem in root.iter():
        if elem.tag.startswith('{'):
            ns_uri = elem.tag.split('}')[0].lstrip('{')
            if 'wordpress.org/export' in ns_uri:
                wp_ns = ns_uri
                break

    if not wp_ns:
        # Fallback — try common versions
        for ver in ('1.2', '1.1', '1.0'):
            candidate = f'http://wordpress.org/export/{ver}/'
            if root.find(f'.//{{{candidate}}}post_type') is not None:
                wp_ns = candidate
                break

    if not wp_ns:
        wp_ns = 'http://wordpress.org/export/1.2/'  # last-resort default

    return {
        'wp': wp_ns,
        'content': content_ns,
        'dc': dc_ns,
    }


# ---------------------------------------------------------------------------
# XML Parsing
# ---------------------------------------------------------------------------

def parse_wordpress_xml(
    xml_source,
    *,
    post_types: set[str] | None = None,
    post_statuses: set[str] | None = None,
) -> list[dict]:
    """
    Parse a WordPress WXR XML export and return a list of post dicts.

    Parameters
    ----------
    xml_source : str | Path | file-like
        Path to an XML file **or** a file-like object (e.g. BytesIO).
    post_types : set[str] | None
        Which post types to include (e.g. {'post', 'page'}).
        ``None`` means *all* types.
    post_statuses : set[str] | None
        Which statuses to include (e.g. {'publish', 'draft'}).
        ``None`` means *all* statuses.
    """
    tree = ET.parse(xml_source)
    root = tree.getroot()
    ns = _detect_wp_namespace(root)

    posts: list[dict] = []

    for item in root.findall('.//item'):
        # --- Filter by type ---
        ptype_el = item.find(f"{{{ns['wp']}}}post_type")
        ptype = ptype_el.text if ptype_el is not None and ptype_el.text else 'post'
        if post_types is not None and ptype not in post_types:
            continue

        # --- Filter by status ---
        status_el = item.find(f"{{{ns['wp']}}}status")
        status = status_el.text if status_el is not None and status_el.text else ''
        if post_statuses is not None and status not in post_statuses:
            continue

        # --- Extract fields ---
        title_el = item.find('title')
        content_el = item.find(f"{{{ns['content']}}}encoded")
        date_el = item.find(f"{{{ns['wp']}}}post_date")
        slug_el = item.find(f"{{{ns['wp']}}}post_name")

        # Categories & tags
        categories = []
        tags = []
        for cat in item.findall('category'):
            domain = cat.attrib.get('domain', '')
            text = cat.text or ''
            if domain == 'category':
                categories.append(text)
            elif domain == 'post_tag':
                tags.append(text)

        posts.append({
            'title': title_el.text if title_el is not None and title_el.text else 'Untitled',
            'content': content_el.text if content_el is not None else '',
            'date': date_el.text if date_el is not None else '',
            'slug': slug_el.text if slug_el is not None else '',
            'type': ptype,
            'status': status,
            'categories': categories,
            'tags': tags,
        })

    return posts


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown_files(
    posts: list[dict],
    *,
    date_prefix: bool = True,
    yaml_frontmatter: bool = False,
) -> list[tuple[str, str]]:
    """
    Convert a list of post dicts to ``(filename, markdown_content)`` tuples.

    Parameters
    ----------
    date_prefix : bool
        Prepend ``YYYYMMDD-`` to each filename.
    yaml_frontmatter : bool
        If True, emit YAML front-matter (``---`` block) instead of an inline
        ``# Title`` + ``*Published: …*`` header.
    """
    results: list[tuple[str, str]] = []

    for post in posts:
        md_body = html_to_markdown(post['content'])

        # ---- Filename ----
        base = post['slug'] if post['slug'] else sanitize_filename(post['title'])
        prefix = ''
        if date_prefix and post['date']:
            try:
                dt = datetime.strptime(post['date'], '%Y-%m-%d %H:%M:%S')
                prefix = dt.strftime('%Y%m%d') + '-'
            except ValueError:
                try:
                    dt = datetime.strptime(post['date'].split()[0], '%Y-%m-%d')
                    prefix = dt.strftime('%Y%m%d') + '-'
                except Exception:
                    pass
        filename = f"{prefix}{base}.md"

        # ---- Header ----
        if yaml_frontmatter:
            lines = ['---']
            lines.append(f"title: \"{post['title']}\"")
            if post['date']:
                lines.append(f"date: {post['date']}")
            if post.get('categories'):
                lines.append(f"categories: {post['categories']}")
            if post.get('tags'):
                lines.append(f"tags: {post['tags']}")
            lines.append('---')
            lines.append('')
            lines.append(md_body)
            content = '\n'.join(lines)
        else:
            parts = [f"# {post['title']}\n"]
            if post['date']:
                parts.append(f"*Published: {post['date']}*\n")
            parts.append(md_body)
            content = '\n'.join(parts)

        results.append((filename, content))

    return results


# ---------------------------------------------------------------------------
# CLI entry-point (kept for convenience)
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert WordPress XML export to Markdown files.')
    parser.add_argument('xml_file', help='Path to the WordPress WXR XML export file.')
    parser.add_argument('-o', '--output', default='posts', help='Output directory (default: posts).')
    parser.add_argument('--types', nargs='*', default=['post'], help='Post types to include (default: post).')
    parser.add_argument('--statuses', nargs='*', default=['publish'], help='Post statuses to include (default: publish).')
    parser.add_argument('--no-date-prefix', action='store_true', help='Omit YYYYMMDD date prefix from filenames.')
    parser.add_argument('--yaml', action='store_true', help='Use YAML front-matter instead of inline heading.')
    args = parser.parse_args()

    print("Parsing WordPress XML…")
    posts = parse_wordpress_xml(
        args.xml_file,
        post_types=set(args.types),
        post_statuses=set(args.statuses),
    )
    print(f"Found {len(posts)} matching items")

    files = generate_markdown_files(
        posts,
        date_prefix=not args.no_date_prefix,
        yaml_frontmatter=args.yaml,
    )

    os.makedirs(args.output, exist_ok=True)
    for fname, content in files:
        fpath = os.path.join(args.output, fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Created: {fpath}")

    print(f"\nDone — {len(files)} file(s) written to '{args.output}'.")


if __name__ == '__main__':
    main()
