from __future__ import annotations

DEFAULT_MARKDOWN_PROMPT = """Attached is one page from a PDF paper or technical document.

Convert the page to clean Markdown for downstream paper analysis.

Return exactly this shape:

---
primary_language: <two-letter language code, or null when no readable text exists>
is_rotation_valid: <true or false>
rotation_correction: <0, 90, 180, or 270>
is_table: <true or false>
is_diagram: <true or false>
---
<page markdown>

Rules:
- Preserve the natural reading order.
- Preserve headings, paragraphs, lists, equations, references, captions, footnotes, and tables when they are readable.
- Convert tables to Markdown tables when compact, or HTML tables when Markdown tables would lose structure.
- Convert math to LaTeX.
- For charts, diagrams, and figures, include a concise Markdown image placeholder with useful alt text.
- If the page is rotated, set is_rotation_valid to false and set rotation_correction to the clockwise correction needed to read the text.
- If no readable text exists, use null for primary_language and leave the Markdown body empty.
- Do not invent content that is not visible on the page.
"""
