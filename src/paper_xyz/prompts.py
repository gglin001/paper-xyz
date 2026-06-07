from __future__ import annotations

DEFAULT_MARKDOWN_PROMPT = """Convert the document image to Markdown. Preserve headings, paragraphs, lists, tables, formulas, and reading order. Do not invent content.
"""

GLM_OCR_MARKDOWN_PROMPT = """Recognize the text in the image and output in Markdown format. Preserve the original layout (headings/paragraphs/tables/formulas). Do not fabricate content that does not exist in the image.
"""

DOTS_LAYOUT_JSON_PROMPT = """Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]

2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].

3. Text Extraction & Formatting Rules:
    - Picture: For the 'Picture' category, the text field should be omitted.
    - Formula: Format its text as LaTeX.
    - Table: Format its text as HTML.
    - All Others (Text, Title, etc.): Format their text as Markdown.

4. Constraints:
    - The output text must be the original text from the image, with no translation.
    - All layout elements must be sorted according to human reading order.

5. Final Output: The entire output must be a single JSON object.
"""

DEEPSEEK_OCR_MARKDOWN_PROMPT = """Convert the document to markdown.
"""

FIRERED_OCR_MARKDOWN_PROMPT = """You are an AI assistant specialized in converting PDF images to Markdown format. Please follow these instructions for the conversion:

1. Text Processing:
- Accurately recognize all text content in the PDF image without guessing or inferring.
- Convert the recognized text into Markdown format.
- Maintain the original document structure, including headings, paragraphs, lists, etc.

2. Mathematical Formula Processing:
- Convert all mathematical formulas to LaTeX format.
- Enclose inline formulas with,(,). For example: This is an inline formula,( E = mc^2,)
- Enclose block formulas with,\\[,\\]. For example:,[,frac{-b,pm,sqrt{b^2 - 4ac}}{2a},]

3. Table Processing:
- Convert tables to HTML format.
- Wrap the entire table with <table> and </table>.

4. Figure Handling:
- Ignore figures content in the PDF image. Do not attempt to describe or convert images.

5. Output Format:
- Ensure the output Markdown document has a clear structure with appropriate line breaks between elements.
- For complex layouts, try to maintain the original document's structure and format as closely as possible.

Please strictly follow these guidelines to ensure accuracy and consistency in the conversion. Your task is to accurately convert the content of the PDF image into Markdown format without adding any extra explanations or comments.
"""
