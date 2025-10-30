from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QTextBrowser
import markdown
import re


def clean_markdown(markdown_text: str) -> str:
    """Clean and standardize markdown by removing custom components and malformed elements"""

    # Remove CodeGroup tags completely
    markdown_text = markdown_text.replace('<CodeGroup>', '')
    markdown_text = markdown_text.replace('</CodeGroup>', '')

    # Remove leading whitespace from lines that start with ```
    lines = markdown_text.split('\n')
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith('```'):
            cleaned_lines.append(line.strip())  # Remove ALL leading whitespace from fence markers
        else:
            cleaned_lines.append(line)
    markdown_text = '\n'.join(cleaned_lines)

    # Convert Info/Warning/Note blocks to blockquotes
    markdown_text = re.sub(
        r'<Info>(.*?)</Info>',
        lambda m: f"\n> **Info:** {' '.join(m.group(1).strip().split())}\n",
        markdown_text,
        flags=re.DOTALL
    )

    # Simplify images
    markdown_text = re.sub(
        r'<img[^>]+src="([^"]+)"[^>]+alt="([^"]+)"[^>]*>',
        r'![\2](\1)',
        markdown_text
    )

    # Clean language identifiers like "bash pip" -> "bash"
    markdown_text = re.sub(r'^```(\w+)\s+\w+.*$', r'```\1', markdown_text, flags=re.MULTILINE)

    # Clean up excessive newlines
    markdown_text = re.sub(r'\n{4,}', '\n\n', markdown_text)

    return markdown_text.strip()


def __init__(self, markdown_text: str, title: str = "Markdown Preview", parent=None, clean: bool = True):
    super().__init__(parent)
    self.setWindowTitle(title)
    self.setModal(True)
    self.resize(960, 720)

    layout = QVBoxLayout(self)

    # Clean the markdown if requested
    if clean:
        markdown_text = clean_markdown(markdown_text)
        print(f"✓ Markdown cleaned")

    # Use QTextBrowser with HTML rendering
    self.view = QTextBrowser(self)
    self.view.setOpenExternalLinks(True)

    # Convert markdown to HTML
    html = markdown.markdown(
        markdown_text,
        extensions=[
            'fenced_code',
            'tables',
            'nl2br',
            'sane_lists',
            'codehilite',
            'toc',
            'extra'
        ]
    )


class MarkdownDialog(QDialog):
    def __init__(self, markdown_text: str, title: str = "Markdown Preview", parent=None, clean: bool = True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(960, 720)

        layout = QVBoxLayout(self)

        # Clean the markdown if requested
        if clean:
            markdown_text = clean_markdown(markdown_text)
            print(f"✓ Markdown cleaned")

        # Use QTextBrowser with HTML rendering
        self.view = QTextBrowser(self)
        self.view.setOpenExternalLinks(True)

        # Convert markdown to HTML using the markdown library
        html_body = markdown.markdown(
            markdown_text,
            extensions=[
                'fenced_code',
                'tables',
                'nl2br',
                'sane_lists',
                'extra'
            ]
        )

        # Wrap in a styled container
        styled_html = f"""
        <html>
        <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                color: #24292e;
                background-color: #ffffff;
                padding: 20px;
                max-width: 100%;
            }}
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                line-height: 1.25;
            }}
            h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h3 {{ font-size: 1.25em; }}
            code {{
                background-color: rgba(175, 184, 193, 0.2);
                border-radius: 3px;
                font-size: 85%;
                margin: 0;
                padding: 0.2em 0.4em;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                color: #24292e;
            }}
            pre {{
                background-color: #e8eef5;  /* Changed from #f6f8fa to darker blue-gray */
                border: 1px solid #c8d3e0;  /* Slightly darker border to match */
                border-radius: 6px;
                font-size: 13px;
                line-height: 1.45;
                overflow: auto;
                padding: 16px;
                margin: 16px 0;
            }}
            pre code {{
                background-color: transparent;
                border: 0;
                display: block;
                line-height: inherit;
                margin: 0;
                overflow: visible;
                padding: 0;
                color: #24292e;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                white-space: pre;
            }}
            blockquote {{
                border-left: 4px solid #0969da;
                color: #57606a;
                padding-left: 1em;
                margin-left: 0;
                background-color: #f6f8fa;
                padding: 8px 16px;
                border-radius: 3px;
            }}
            table {{
                border-collapse: collapse;
                border-spacing: 0;
                width: 100%;
            }}
            table th {{
                font-weight: 600;
                background-color: #f6f8fa;
            }}
            table th, table td {{
                border: 1px solid #dfe2e5;
                padding: 6px 13px;
            }}
            ul, ol {{
                padding-left: 2em;
            }}
            a {{
                color: #0969da;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
        </head>
        <body>
        {html_body}
        </body>
        </html>
        """

        self.view.setHtml(styled_html)
        layout.addWidget(self.view)

        # Add close button
        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def show_modal(parent, markdown_text: str, title: str = "Markdown Preview", clean: bool = True):
        dlg = MarkdownDialog(markdown_text, title, parent, clean=clean)
        return dlg.exec()
