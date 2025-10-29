# web_scraping_tab.py
"""
Web Scraping Tab for Knowledge Capture Tool
Intelligent content extraction with multiple fallback strategies
"""

import logging
import re
import random
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QCheckBox, QProgressBar, QComboBox,
    QTextEdit, QMessageBox, QSplitter, QTabWidget, QFormLayout
)
from PySide6.QtCore import Qt, QThread, Signal
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time

_LOGGER = logging.getLogger(__name__)


class DomainRateLimiter:
    """Per-domain rate limiter to prevent overwhelming servers"""

    def __init__(self):
        self.domain_timestamps = defaultdict(list)
        self.requests_per_minute = 10
        self.requests_per_hour = 100

    def wait_if_needed(self, domain: str):
        """Wait if necessary to respect rate limits for this domain"""
        now = time.time()

        # Clean old timestamps (older than 1 hour)
        self.domain_timestamps[domain] = [
            ts for ts in self.domain_timestamps[domain]
            if now - ts < 3600
        ]

        timestamps = self.domain_timestamps[domain]

        # Check hourly limit
        if len(timestamps) >= self.requests_per_hour:
            oldest = min(timestamps)
            wait_time = 3600 - (now - oldest)
            if wait_time > 0:
                _LOGGER.warning(f"Hourly limit reached for {domain}, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                now = time.time()

        # Check per-minute limit
        recent = [ts for ts in timestamps if now - ts < 60]
        if len(recent) >= self.requests_per_minute:
            oldest_recent = min(recent)
            wait_time = 60 - (now - oldest_recent)
            if wait_time > 0:
                _LOGGER.info(f"Per-minute limit reached for {domain}, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                now = time.time()

        # Add current request timestamp
        self.domain_timestamps[domain].append(now)

        # Add randomized delay (2-5 seconds) for politeness
        random_delay = random.uniform(2.0, 5.0)
        _LOGGER.info(f"Adding polite delay: {random_delay:.1f}s")
        time.sleep(random_delay)


# Global rate limiter instance (shared across all scraping operations)
_rate_limiter = DomainRateLimiter()


@dataclass
class WebScrapingResult:
    """Result from web scraping"""
    url: str
    success: bool
    content: str = ""
    title: str = ""
    method_used: str = ""
    extraction_quality: str = ""
    word_count: int = 0
    error: Optional[str] = None
    metadata: Dict = None


class WebScraperProcessor(QThread):
    """Background thread for web scraping with intelligent content extraction"""

    # Signals FIRST
    processing_progress = Signal(str)
    processing_completed = Signal(object)  # WebScrapingResult
    processing_failed = Signal(str)

    def __init__(self,
                 url: str,
                 method: str,
                 content_selector: str,
                 exclude_patterns: str,
                 wait_time: int,
                 parent=None):
        super().__init__(parent)  # important: pass parent to QThread
        self.url = url
        self.method = method
        self.content_selector = content_selector.strip()
        self.exclude_patterns = [p.strip() for p in exclude_patterns.split(',') if p.strip()]
        self.wait_time = wait_time
        self.user_agent = "DataWoven/1.0 (Knowledge Capture Tool)"

    # ====== Smart extraction helpers (non-breaking additions) ======
    _JS_COLLECT = """() => {
      const visited = new WeakSet();

      function visible(el) {
        const st = getComputedStyle(el);
        if (!st || st.display === "none" || st.visibility === "hidden" || st.opacity === "0") return false;
        // Skip elements that are visually tiny (common for hidden mobile/desktop dupes)
        const r = el.getBoundingClientRect();
        if ((r.width === 0 || r.height === 0) && !el.shadowRoot) return false;
        return true;
      }

      function shouldSkip(el) {
        // Skip nav/TOC/breadcrumbs/social/newsletter/etc.
        if (el.closest('nav,aside,header,footer,[role="navigation"],[aria-hidden="true"],[hidden]')) return true;
        const cl = (el.className || "").toString().toLowerCase();
        if (cl.includes("toc") || cl.includes("table-of-contents") || cl.includes("breadcrumbs") ||
            cl.includes("social") || cl.includes("newsletter") || cl.includes("cookie")) return true;
        // Skip obvious card grids / promos that duplicate body text
        if (cl.includes("card") || cl.includes("tile") || cl.includes("promo")) return true;
        return false;
      }

      function isParagraphish(el) {
        const tag = (el.tagName || "").toLowerCase();
        return /^h[1-6]$/.test(tag) || ["p","li","blockquote"].includes(tag);
      }

      function dive(el, acc) {
        if (!el || visited.has(el)) return;
        visited.add(el);
        if (!visible(el) || shouldSkip(el)) return;

        if (isParagraphish(el)) {
          const t = (el.innerText || "").trim();
          if (t) acc.push(t);
        }

        // Shadow DOM
        if (el.shadowRoot) Array.from(el.shadowRoot.children).forEach(c => dive(c, acc));

        // Light DOM
        Array.from(el.children).forEach(c => dive(c, acc));
      }

      // Prefer article/main roots
      const roots = document.querySelectorAll("main, article, [role='main']");
      const acc = [];
      if (roots.length) Array.from(roots).forEach(r => dive(r, acc));
      else dive(document.body, acc);

      return acc.join("\\n\\n");
    }"""

    def _normalize_ws(self, text: str) -> str:
        import re
        return re.sub(r"\s+", " ", (text or "")).strip()

    def _clean_newlines(self, text: str) -> str:
        """
        Remove stray literal '\n' and excessive real newlines.
        Keeps paragraph spacing but avoids artifacts like '\\n' or too many blank lines.
        """
        if not text:
            return ""
        import re
        # Replace literal backslash-n sequences
        text = text.replace("\\n", " ")
        # Collapse multiple newlines down to two
        text = re.sub(r"\n\s*\n\s*", "\n\n", text)
        # Collapse single newlines surrounded by text into spaces
        text = re.sub(r"([^\n])\n([^\n])", r"\1 \2", text)
        # Normalize whitespace overall
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _extract_main_text_from_html_smart(self, html: str) -> str:
        """Try trafilatura -> readability-lxml -> existing intelligent soup heuristics."""
        try:
            # Try trafilatura if available
            try:
                import trafilatura  # type: ignore
                txt = trafilatura.extract(html, include_comments=False, include_tables=False)
                if txt and len(txt.split()) > 120:
                    return txt.strip()
            except Exception:
                pass
            # Try readability-lxml if available
            try:
                from readability import Document  # type: ignore
                doc = Document(html)
                summary_html = doc.summary(html_partial=True)
                if summary_html:
                    try:
                        from lxml import html as lxml_html  # type: ignore
                        root = lxml_html.fromstring(summary_html)
                        text = self._normalize_ws(root.text_content())
                    except Exception:
                        import re as _re
                        text = _re.sub(r"<[^>]+>", " ", summary_html)
                    if text and len(text.split()) > 120:
                        return text
            except Exception:
                pass
        except Exception:
            pass
        # Fallback to existing path
        try:
            from bs4 import BeautifulSoup
            parser = "lxml" if "lxml" in sys.modules else "html.parser"
            soup = BeautifulSoup(html, parser)
            return self.extract_content_intelligent(soup)
        except Exception:
            return ""

    def _browser_extract_dom_smart(self, page) -> str:
        """Shadow-aware composed DOM and accessibility tree extraction (sync Playwright)."""
        out_candidates = []

        # A11y tree
        try:
            root = None
            try:
                main = page.locator("main, article, [role='main']").first
                if main and main.count():
                    root = main
            except Exception:
                root = None
            ax = page.accessibility.snapshot(root=root) if hasattr(page, "accessibility") else None
            buf = []

            def walk(node):
                if not node: return
                role = (node.get("role") or "").lower()
                name = (node.get("name") or "") or ""
                value = (node.get("value") or "") or ""
                if role in {"heading", "paragraph", "listitem", "list", "text"}:
                    text = name if role == "heading" else (value or name)
                    if text and text.strip():
                        buf.append(text.strip())
                for c in (node.get("children") or []):
                    walk(c)

            if ax:
                walk(ax)
                if buf and len(" ".join(buf).split()) > 40:
                    out_candidates.append("\\n\\n".join(buf))
        except Exception:
            pass

        # Composed DOM walker (pierces shadow roots)
        try:
            text_js = page.evaluate(self._JS_COLLECT)
            if text_js and len(text_js.split()) > 40:
                text_js = self._dedupe_text(text_js)
                text_js = self._dedupe_fuzzy(text_js)  # optional; comment out if you prefer exact only
                out_candidates.append(text_js)
        except Exception:
            pass

        # Readability.js
        try:
            page.add_script_tag(url="https://unpkg.com/@mozilla/readability@0.4.4/Readability.js")
            text_rb = page.evaluate(
                "() => { try { return new Readability(document).parse()?.textContent || '' } catch(e){ return '' } }"
            )
            if text_rb and len(text_rb.split()) > 40:
                text_rb = self._dedupe_text(text_rb)
                out_candidates.append(text_rb)
        except Exception:
            pass
        if out_candidates:
            text = max(out_candidates, key=lambda t: len(t.split())).strip()
            text = self._dedupe_text(text)
            text = self._clean_newlines(text)
            return text

        # Fallback to existing soup-based extraction from HTML
        try:
            html = page.content()
            return self._extract_main_text_from_html_smart(html)
        except Exception:
            return ""

    def _dedupe_text(self, text: str, min_len: int = 20) -> str:
        """Order-preserving exact de-duplication on paragraph blocks."""
        seen = set()
        out = []
        for para in (p.strip() for p in text.split("\n\n")):
            if len(para) < min_len:
                continue
            key = self._normalize_ws(para).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(para)
        return "\n\n".join(out)

    def _dedupe_fuzzy(self, text: str, min_len: int = 40, similarity: float = 0.92) -> str:
        """
        Optional: light fuzzy de-duplication to catch near-duplicates (TOC vs heading line with punctuation).
        Uses difflib; fast enough for a page.
        """
        from difflib import SequenceMatcher
        canon = []  # normalized paragraphs for comparison
        out = []
        for para in (p.strip() for p in text.split("\n\n")):
            if len(para) < min_len:
                out.append(para)  # keep small bits; they’re unlikely duplicates
                continue
            n = self._normalize_ws(para).lower()
            if any(SequenceMatcher(None, n, c).ratio() >= similarity for c in canon):
                continue
            canon.append(n)
            out.append(para)
        return "\n\n".join(out)

    def run(self):
        """Execute web scraping with intelligent fallback"""
        try:
            # Apply domain-specific rate limiting
            parsed = urlparse(self.url)
            domain = parsed.netloc

            self.processing_progress.emit(f"Checking rate limits for {domain}...")
            _rate_limiter.wait_if_needed(domain)

            # Try extraction based on method
            if self.method == "auto":
                result = self.try_auto_extraction()
            elif self.method == "simple":
                result = self.try_simple_http()
            else:  # browser
                result = self.try_browser_extraction()

            if result.success:
                self.processing_completed.emit(result)
            else:
                self.processing_failed.emit(result.error or "Unknown error")

        except Exception as e:
            _LOGGER.error(f"Web scraping failed: {e}")
            self.processing_failed.emit(str(e))


    def check_robots_txt(self) -> bool:
        """Check if robots.txt allows scraping"""
        try:
            parsed = urlparse(self.url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            response = requests.get(robots_url, timeout=5,
                                    headers={'User-Agent': self.user_agent})

            if response.status_code == 200:
                # Simple check - look for Disallow directives
                # In production, use robotparser module
                if "Disallow: /" in response.text:
                    return False
            return True
        except:
            # If robots.txt doesn't exist or can't be fetched, assume allowed
            return True


    def try_auto_extraction(self) -> WebScrapingResult:
        """Try intelligent extraction, fallback to browser if needed"""
        self.processing_progress.emit("Trying intelligent extraction...")

        result = self.try_simple_http()

        # Check quality score - if poor or failed, try browser
        if not result.success or result.word_count < 100:
            self.processing_progress.emit("Content quality low or failed, trying browser mode...")
            time.sleep(1)  # Brief pause before browser
            return self.try_browser_extraction()

        return result


    def try_simple_http(self) -> WebScrapingResult:
        """Simple HTTP request with intelligent content extraction"""
        max_retries = 2
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.processing_progress.emit("Fetching page...")

                headers = {
                    'User-Agent': self.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9'
                }

                response = requests.get(self.url, headers=headers, timeout=30)

                # Handle rate limiting (429) and server errors (503)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    _LOGGER.warning(f"Rate limited (429), waiting {retry_after}s before retry")
                    self.processing_progress.emit(f"Rate limited - waiting {retry_after}s...")
                    time.sleep(retry_after)
                    retry_count += 1
                    continue

                elif response.status_code == 503:
                    # Server temporarily unavailable - exponential backoff
                    wait_time = (2 ** retry_count) * 5  # 5s, 10s, 20s
                    _LOGGER.warning(f"Server unavailable (503), waiting {wait_time}s before retry")
                    self.processing_progress.emit(f"Server busy - waiting {wait_time}s...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue

                # Raise for other HTTP errors
                response.raise_for_status()

                self.processing_progress.emit("Extracting content...")

                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract title
                title = self.extract_title(soup)

                # Extract content using intelligent methods
                content = self._extract_main_text_from_html_smart(response.text)
                if not content or len(content.split()) < 50:
                    content = self.extract_content_intelligent(soup)

                # Calculate quality metrics
                word_count = len(content.split())
                quality = self.assess_content_quality(content)

                return WebScrapingResult(
                    url=self.url,
                    success=True,
                    content=content,
                    title=title,
                    method_used="simple_http",
                    extraction_quality=quality,
                    word_count=word_count
                )

            except requests.exceptions.HTTPError as e:
                if retry_count < max_retries - 1:
                    wait_time = (2 ** retry_count) * 3
                    _LOGGER.warning(f"HTTP error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    retry_count += 1
                else:
                    return WebScrapingResult(
                        url=self.url,
                        success=False,
                        error=f"HTTP Error after {max_retries} retries: {str(e)}"
                    )

            except Exception as e:
                return WebScrapingResult(
                    url=self.url,
                    success=False,
                    error=str(e)
                )

        return WebScrapingResult(
            url=self.url,
            success=False,
            error=f"Failed after {max_retries} retries"
        )


    def try_browser_extraction(self) -> WebScrapingResult:
        """Browser automation with Playwright (requires installation)"""
        try:
            # Try to import playwright
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                return WebScrapingResult(
                    url=self.url,
                    success=False,
                    error="Playwright not installed. Install with: pip install playwright && playwright install chromium"
                )

            self.processing_progress.emit("Launching browser...")

            with sync_playwright() as p:
                # Launch browser with extended timeout
                browser = p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )

                context = browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )

                page = context.new_page()

                # Set longer default timeout
                page.set_default_timeout(60000)  # 60 seconds

                self.processing_progress.emit("Loading page...")

                try:
                    # Try with domcontentloaded (faster, more reliable than networkidle)
                    page.goto(self.url, wait_until="domcontentloaded", timeout=45000)

                    self.processing_progress.emit("Waiting for content to render...")

                    # Wait for common content indicators
                    try:
                        page.wait_for_selector(
                            'article, main, .content, [role="main"], p',
                            timeout=10000,
                            state='visible'
                        )
                    except:
                        # If no common selectors found, just wait a bit
                        pass

                    # Additional wait for JavaScript (user-specified)
                    if self.wait_time > 0:
                        time.sleep(self.wait_time)

                    # Scroll to load lazy content
                    try:
                        page.evaluate("""
                                window.scrollTo(0, document.body.scrollHeight / 2);
                            """)
                        time.sleep(0.5)
                        page.evaluate("""
                                window.scrollTo(0, document.body.scrollHeight);
                            """)
                        time.sleep(0.5)
                        page.evaluate("window.scrollTo(0, 0);")
                    except:
                        pass

                except Exception as e:
                    browser.close()
                    return WebScrapingResult(
                        url=self.url,
                        success=False,
                        error=f"Page load timeout: {str(e)}\n\nTry:\n"
                              "• Increasing wait time\n"
                              "• Using simple mode if site blocks automation\n"
                              "• Checking if site requires login"
                    )

                self.processing_progress.emit("Extracting content...")

                # Get HTML content
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract title and content
                title = self.extract_title(soup)
                content = self._browser_extract_dom_smart(page) or self.extract_content_intelligent(soup)

                browser.close()

                word_count = len(content.split())
                quality = self.assess_content_quality(content)

                return WebScrapingResult(
                    url=self.url,
                    success=True,
                    content=content,
                    title=title,
                    method_used="browser",
                    extraction_quality=quality,
                    word_count=word_count
                )

        except Exception as e:
            return WebScrapingResult(
                url=self.url,
                success=False,
                error=f"Browser extraction failed: {str(e)}\n\n"
                      "Troubleshooting:\n"
                      "• Ensure Playwright is installed: pip install playwright\n"
                      "• Run: playwright install chromium\n"
                      "• Try 'simple' mode instead"
            )


    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        try:
            # Try various title sources
            if soup.title and soup.title.string:
                return soup.title.string.strip()

            # Try h1
            h1 = soup.find('h1')
            if h1:
                return h1.get_text().strip()

            # Try og:title meta tag
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                return og_title.get('content').strip()

            # Try regular meta title
            meta_title = soup.find('meta', attrs={'name': 'title'})
            if meta_title and meta_title.get('content'):
                return meta_title.get('content').strip()

        except Exception as e:
            _LOGGER.warning(f"Error extracting title: {e}")

        return "Untitled"


    def extract_content_intelligent(self, soup: BeautifulSoup) -> str:
        """Intelligent content extraction with multiple strategies"""

        try:
            # Remove unwanted elements first
            self.remove_unwanted_elements(soup)

            # Strategy 1: User-specified selector (if provided)
            if self.content_selector:
                content = self.extract_by_selector(soup, self.content_selector)
                if content and len(content.split()) > 50:
                    return self.clean_text(content)

            # Strategy 2: Try readability-style extraction
            content = self.extract_by_readability(soup)
            if content and len(content.split()) > 50:
                return self.clean_text(content)

            # Strategy 3: Common semantic tags
            content = self.extract_by_semantic_tags(soup)
            if content and len(content.split()) > 50:
                return self.clean_text(content)

            # Strategy 4: Fallback - largest text block
            content = self.extract_largest_text_block(soup)
            if content:
                return self.clean_text(content)

        except Exception as e:
            _LOGGER.error(f"Content extraction error: {e}")

        return "No content could be extracted from this page."


    def remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove navigation, footer, ads, etc."""
        try:
            # Standard unwanted tags
            for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside']:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove common sidebar/related content sections by text patterns
            sidebar_patterns = [
                'related', 'resources', 'you might also like', 'recommended',
                'popular posts', 'recent posts', 'categories', 'tags',
                'newsletter', 'subscribe', 'follow us', 'social media',
                'advertisement', 'sponsored'
            ]

            for element in soup.find_all(['div', 'section', 'aside']):
                try:
                    element_text = element.get_text().lower()[:200]  # Check first 200 chars

                    # Check if element looks like sidebar/related content
                    if any(pattern in element_text for pattern in sidebar_patterns):
                        element.decompose()
                        continue

                    # Remove if class/id suggests it's unwanted
                    classes = ' '.join(element.get('class', [])).lower()
                    element_id = str(element.get('id', '')).lower()

                    if any(pattern in classes or pattern in element_id for pattern in sidebar_patterns):
                        element.decompose()
                except:
                    pass  # Skip elements that cause issues

            # Remove by exclude patterns (user-specified)
            for pattern in self.exclude_patterns:
                try:
                    # Remove by class
                    for element in soup.find_all(class_=re.compile(pattern, re.I)):
                        element.decompose()

                    # Remove by id
                    for element in soup.find_all(id=re.compile(pattern, re.I)):
                        element.decompose()

                    # Remove by tag with pattern in text
                    for element in soup.find_all(True):
                        if pattern.lower() in str(element.get('class', '')).lower():
                            element.decompose()
                except:
                    pass  # Skip patterns that cause issues

        except Exception as e:
            _LOGGER.warning(f"Error removing unwanted elements: {e}")


    def extract_by_selector(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract content using CSS selector"""
        try:
            elements = soup.select(selector)
            if elements:
                return '\n\n'.join(el.get_text(separator='\n', strip=True) for el in elements if el)
        except Exception as e:
            _LOGGER.warning(f"Selector extraction error: {e}")
        return ""


    def extract_by_readability(self, soup: BeautifulSoup) -> str:
        """Extract main content using tag-agnostic content pattern analysis"""
        candidates = []

        try:
            # Look at ALL elements, regardless of tag name
            # Only exclude known junk tags
            for element in soup.find_all(True):  # True = all tags
                try:
                    if not element:
                        continue

                    # Skip elements we know are junk
                    if element.name in ['script', 'style', 'meta', 'link', 'noscript',
                                        'svg', 'path', 'button', 'input', 'form']:
                        continue

                    # Get text content
                    text = element.get_text(separator=' ', strip=True)

                    # Skip if too short (not a content block)
                    word_count = len(text.split())
                    if word_count < 50:
                        continue

                    # Analyze CONTENT patterns, not tag names

                    # Count text structure elements (regardless of tag)
                    children = element.find_all(True, recursive=False)
                    text_blocks = [c for c in children if c.get_text(strip=True)]
                    link_elements = element.find_all(True, href=True)  # Any tag with href

                    # Calculate content metrics
                    link_count = len(link_elements)
                    link_density = link_count / max(word_count, 1)

                    # Check if element has substantial nested text blocks
                    has_structure = len(text_blocks) > 2

                    # Sentence detection (good content has proper sentences)
                    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
                    sentence_count = len(sentences)
                    avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

                    # Check for paragraph-like content (50+ chars with punctuation)
                    has_paragraph_content = any(
                        len(s) > 50 and any(p in s for p in ['.', '!', '?'])
                        for s in text.split('\n')
                    )

                    # Class/ID analysis (still useful for hints)
                    element_classes = ' '.join(element.get('class', []) or []).lower()
                    element_id = str(element.get('id') or '').lower()

                    # Positive content indicators
                    content_indicators = [
                        'content', 'main', 'article', 'post', 'entry', 'story',
                        'body', 'text', 'description', 'paragraph'
                    ]

                    has_content_indicator = any(
                        indicator in element_classes or indicator in element_id
                        for indicator in content_indicators
                    )

                    # Negative indicators (sidebar/nav)
                    junk_indicators = [
                        'sidebar', 'related', 'resources', 'widget', 'aside',
                        'recommended', 'popular', 'recent', 'menu', 'nav',
                        'footer', 'header', 'ad', 'banner'
                    ]

                    has_junk_indicator = any(
                        indicator in element_classes or indicator in element_id
                        for indicator in junk_indicators
                    )

                    # CONTENT-BASED SCORING (not tag-based)
                    score = 0

                    # Strong positive signals
                    score += word_count * 0.5  # Raw content volume
                    score += sentence_count * 10  # Well-formed sentences

                    if avg_sentence_length > 8:  # Average sentence has 8+ words
                        score += 50

                    if avg_sentence_length > 15:  # Long sentences = article content
                        score += 100

                    if has_paragraph_content:  # Has paragraph-like blocks
                        score += 100

                    if has_structure:  # Has nested structure
                        score += 30

                    if has_content_indicator:  # Class/ID hint
                        score += 50

                    # Check for repetitive list content (like domain lists, nav items)
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    if len(lines) > 10:
                        # Check if lines are very similar (repetitive lists)
                        avg_line_length = sum(len(l) for l in lines) / len(lines)
                        if avg_line_length < 30:  # Short repetitive lines
                            score -= 200  # Heavy penalty for lists

                    # Check for cookie/legal text patterns
                    legal_keywords = ['cookie', 'privacy', 'consent', 'agree', 'domain',
                                      'terms', 'legal', 'gdpr', 'preferences']
                    text_lower = text.lower()
                    legal_keyword_count = sum(1 for kw in legal_keywords if kw in text_lower)
                    if legal_keyword_count > 3:
                        score -= 300  # Heavy penalty for legal text

                    # Negative signals
                    score -= link_density * 200  # Too many links

                    if has_junk_indicator:
                        score -= 150

                    if link_density > 0.3:  # More than 30% links
                        score -= 100

                    if sentence_count < 3:  # Too few sentences
                        score -= 50

                    # Penalize if mostly short words (navigation text)
                    words = text.split()
                    short_words = [w for w in words if len(w) < 4]
                    if len(short_words) / max(len(words), 1) > 0.5:
                        score -= 30

                    candidates.append((score, element, {
                        'word_count': word_count,
                        'sentences': sentence_count,
                        'links': link_count,
                        'link_density': link_density,
                        'score': score,
                        'tag': element.name
                    }))

                except Exception as e:
                    _LOGGER.debug(f"Error scoring element: {e}")
                    continue

            # Sort by score and return best candidate
            if candidates:
                candidates.sort(reverse=True, key=lambda x: x[0])

                # Debug logging
                _LOGGER.info("Content extraction candidates (tag-agnostic):")
                for i, (score, elem, metrics) in enumerate(candidates[:5]):
                    _LOGGER.info(f"  #{i + 1}: <{metrics['tag']}> score={score:.1f}, "
                                 f"words={metrics['word_count']}, sentences={metrics['sentences']}, "
                                 f"link_density={metrics['link_density']:.2f}")

                best_element = candidates[0][1]
                return best_element.get_text(separator='\n', strip=True)

        except Exception as e:
            _LOGGER.error(f"Readability extraction error: {e}")

        return ""


    def extract_by_semantic_tags(self, soup: BeautifulSoup) -> str:
        """Extract using semantic HTML5 tags and common patterns"""
        # Priority order of semantic tags and common patterns
        semantic_tags = [
            'article',
            'main',
            '[role="main"]',
            '.content',
            '.post',
            '.article',
            'paragraph',  # Custom tags (like IBM uses)
            '[class*="content"]',
            '[class*="article"]'
        ]

        for tag in semantic_tags:
            try:
                if tag.startswith('.'):
                    # Class selector
                    elements = soup.find_all(class_=re.compile(tag[1:], re.I))
                elif tag.startswith('['):
                    # Attribute selector
                    if 'role=' in tag:
                        elements = soup.find_all(True, attrs={'role': 'main'})
                    elif 'class*=' in tag:
                        # Find elements with class containing pattern
                        pattern = tag.split('"')[1]
                        elements = soup.find_all(True, class_=re.compile(pattern, re.I))
                    else:
                        elements = []
                else:
                    # Tag selector (including custom tags like 'paragraph')
                    elements = soup.find_all(tag)

                if elements:
                    # For custom component tags, get ALL matching elements
                    content = '\n\n'.join(el.get_text(separator='\n', strip=True) for el in elements if el)
                    if len(content.split()) > 50:
                        return content
            except Exception as e:
                _LOGGER.debug(f"Error with selector {tag}: {e}")
                continue

        return ""


    def extract_largest_text_block(self, soup: BeautifulSoup) -> str:
        """Fallback: Find the largest block of text"""
        max_text = ""
        max_length = 0

        for element in soup.find_all(['div', 'section', 'article']):
            text = element.get_text(separator=' ', strip=True)
            if len(text) > max_length:
                max_length = len(text)
                max_text = text

        return max_text


    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        # Remove common artifacts
        text = re.sub(r'Share\s+Tweet\s+Share', '', text)
        text = re.sub(r'Click to share on.*?(?=\n|$)', '', text)

        return text.strip()


    def assess_content_quality(self, content: str) -> str:
        """Assess extracted content quality"""
        word_count = len(content.split())

        if word_count < 50:
            return "poor"
        elif word_count < 200:
            return "fair"
        elif word_count < 500:
            return "good"
        else:
            return "excellent"


class WebScrapingTab(QWidget):
    """Web Scraping Tab - Intelligent content extraction from web pages"""

    def __init__(self, parent, shared_components, metadata_panel):
        super().__init__(parent)
        self.parent = parent
        self.shared_components = shared_components
        self.metadata_panel = metadata_panel

        _LOGGER.info("WebScrapingTab initialized")

        self._processing = False
        self._web_processor = None
        self._current_result = None

        self.init_ui()

    def init_ui(self):
        """Initialize the web scraping interface"""
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # URL Input Section
        url_group = QGroupBox("Web Page URL")
        url_layout = QVBoxLayout(url_group)
        url_layout.setContentsMargins(12, 12, 12, 12)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://docs.aws.amazon.com/bedrock/...")
        self.url_input.setFixedHeight(30)
        self.url_input.textChanged.connect(self.update_process_button)
        url_layout.addWidget(self.url_input)

        left_layout.addWidget(url_group)

        # Extraction Method
        method_group = QGroupBox("Extraction Method")
        method_layout = QFormLayout(method_group)
        method_layout.setContentsMargins(12, 12, 12, 12)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["auto", "simple", "browser"])
        self.method_combo.setToolTip(
            "auto: Smart detection with fallback\n"
            "simple: Fast HTTP (no JavaScript)\n"
            "browser: Full rendering (JavaScript support)"
        )
        method_layout.addRow("Method:", self.method_combo)

        self.wait_time_spin = QComboBox()
        self.wait_time_spin.addItems(["1", "2", "3", "5"])
        self.wait_time_spin.setCurrentText("2")
        self.wait_time_spin.setToolTip(
            "Additional wait time for JavaScript to load (browser mode)\n"
            "Note: Automatic rate limiting (2-5s random delay) is always applied"
        )
        method_layout.addRow("Wait Time (s):", self.wait_time_spin)

        left_layout.addWidget(method_group)

        # Content Selection (Advanced)
        content_group = QGroupBox("Content Selection (Optional)")
        content_layout = QFormLayout(content_group)
        content_layout.setContentsMargins(12, 12, 12, 12)

        self.content_selector = QLineEdit()
        self.content_selector.setPlaceholderText("Leave empty for smart detection")
        self.content_selector.setToolTip("CSS selector for main content (e.g., article, .main-content)")
        content_layout.addRow("Content Selector:", self.content_selector)

        # Add "Test Selector" button
        test_selector_layout = QHBoxLayout()
        self.test_selector_btn = QPushButton("Test Selector")
        self.test_selector_btn.setCursor(Qt.PointingHandCursor)
        self.test_selector_btn.setToolTip("Fetch page and show what this selector extracts")
        self.test_selector_btn.clicked.connect(self.test_content_selector)
        test_selector_layout.addWidget(self.test_selector_btn)
        test_selector_layout.addStretch()
        content_layout.addRow("", test_selector_layout)

        # Add common selector examples
        examples_label = QLabel(
            "<b>Common selectors:</b><br>"
            "• <code>article</code> - Main article tag<br>"
            "• <code>.main-content</code> - Element with class 'main-content'<br>"
            "• <code>#content</code> - Element with id 'content'<br>"
            "• <code>div.article-body</code> - Div with class 'article-body'<br>"
            "<br><b>For IBM pages:</b> <code>main, article</code>"
        )
        examples_label.setWordWrap(True)
        examples_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 8px;")
        content_layout.addRow("Examples:", examples_label)

        self.exclude_patterns = QLineEdit()
        self.exclude_patterns.setText("nav, footer, sidebar, ads, comments")
        self.exclude_patterns.setToolTip("Comma-separated patterns to exclude")
        content_layout.addRow("Exclude Patterns:", self.exclude_patterns)

        left_layout.addWidget(content_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(12, 12, 12, 12)

        # Rate limiting info
        rate_limit_label = QLabel(
            "ℹ️ Rate Limiting: Max 10 req/min, 100 req/hour per domain\n"
            "Random delays (2-5s) automatically applied"
        )
        rate_limit_label.setStyleSheet("color: #64748b; font-size: 11px;")
        rate_limit_label.setWordWrap(True)
        options_layout.addWidget(rate_limit_label)

        left_layout.addWidget(options_group)

        # Shared components - summarization
        summary_group, self.ai_provider, self.summary_style, self.summary_length, self.auto_summarize, self.ai_status = self.shared_components.create_summarization_group()
        left_layout.addWidget(summary_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Right panel - Results
        right_panel = self.create_results_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 1000])

    def create_results_panel(self):
        """Create the results display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tab widget for different views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Raw extracted text tab
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setPlaceholderText("Extracted web content will appear here...")
        self.tab_widget.addTab(self.raw_text_edit, "Raw Content")

        # Summary tab
        self.summary_text_edit = QTextEdit()
        self.summary_text_edit.setPlaceholderText("Summarized content will appear here...")
        self.tab_widget.addTab(self.summary_text_edit, "Summary")

        # Final markdown tab
        self.markdown_edit = QTextEdit()
        self.markdown_edit.setPlaceholderText("Final markdown content for export...")
        self.tab_widget.addTab(self.markdown_edit, "Final Markdown")

        # Processing buttons
        button_layout = QHBoxLayout()

        self.process_btn = QPushButton("Process Page(s)")
        self.process_btn.setCursor(Qt.PointingHandCursor)
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setEnabled(False)
        self.process_btn.setFixedHeight(40)
        button_layout.addWidget(self.process_btn)

        self.summarize_btn = QPushButton("Summarize")
        self.summarize_btn.setCursor(Qt.PointingHandCursor)
        self.summarize_btn.clicked.connect(lambda: self.parent.summarize_text('web'))
        self.summarize_btn.setEnabled(False)
        self.summarize_btn.setFixedHeight(40)
        button_layout.addWidget(self.summarize_btn)

        self.generate_markdown_btn = QPushButton("Generate Markdown")
        self.generate_markdown_btn.setCursor(Qt.PointingHandCursor)
        self.generate_markdown_btn.clicked.connect(lambda: self.parent.generate_final_markdown('web'))
        self.generate_markdown_btn.setEnabled(False)
        self.generate_markdown_btn.setFixedHeight(40)
        button_layout.addWidget(self.generate_markdown_btn)

        self.save_btn = QPushButton("Save Content Bundle")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(lambda: self.parent.save_markdown('web'))
        self.save_btn.setEnabled(False)
        self.save_btn.setFixedHeight(40)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        return panel

    def update_process_button(self):
        """Enable/disable process button based on URL"""
        url = self.url_input.text().strip()
        is_valid = url.startswith('http://') or url.startswith('https://')
        self.process_btn.setEnabled(is_valid)
        self.test_selector_btn.setEnabled(is_valid)

    def test_content_selector(self):
        """Test the content selector and show preview"""
        url = self.url_input.text().strip()
        selector = self.content_selector.text().strip()

        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a URL first.")
            return

        if not selector:
            QMessageBox.information(
                self,
                "No Selector",
                "Enter a CSS selector to test (e.g., 'article', '.main-content', '#content')"
            )
            return

        try:
            # Quick fetch without rate limiting (test only)
            headers = {'User-Agent': 'DataWoven/1.0 (Knowledge Capture Tool)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try the selector
            elements = soup.select(selector)

            if not elements:
                QMessageBox.warning(
                    self,
                    "No Match",
                    f"Selector '{selector}' didn't match any elements on the page.\n\n"
                    "Try:\n"
                    "• Inspecting the page (F12) to find the right selector\n"
                    "• Using more specific selectors like 'div.content' or '#main-article'\n"
                    "• Leaving it empty for automatic detection"
                )
                return

            # Show preview
            preview_text = []
            for i, elem in enumerate(elements[:3], 1):  # Show first 3 matches
                text = elem.get_text(separator=' ', strip=True)
                word_count = len(text.split())
                preview_text.append(
                    f"Match #{i} ({word_count} words):\n{text[:300]}{'...' if len(text) > 300 else ''}\n"
                )

            QMessageBox.information(
                self,
                "Selector Test Results",
                f"Found {len(elements)} element(s) matching '{selector}':\n\n" +
                "\n---\n".join(preview_text)
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Test Failed",
                f"Failed to test selector:\n\n{str(e)}"
            )

    def start_processing(self):
        """Start web scraping process"""
        url = self.url_input.text().strip()

        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a URL to scrape.")
            return

        _LOGGER.info(f"Starting web scraping: {url}")

        # Clear previous results
        self.raw_text_edit.clear()
        self.summary_text_edit.clear()
        self.markdown_edit.clear()

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.process_btn.setEnabled(False)

        # Auto-populate metadata
        self.metadata_panel.original_source.setText(url)
        if not self.metadata_panel.title_input.text().strip():
            parsed = urlparse(url)
            self.metadata_panel.title_input.setText(f"Content from {parsed.netloc}")

        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage(f"Scraping {url}...")

        # Start web scraper thread
        self._web_processor = WebScraperProcessor(
            url=url,
            method=self.method_combo.currentText(),
            content_selector=self.content_selector.text(),
            exclude_patterns=self.exclude_patterns.text(),
            wait_time=int(self.wait_time_spin.currentText()),
        )
        self._web_processor.processing_progress.connect(self.handle_processing_progress)
        self._web_processor.processing_completed.connect(self.handle_processing_completed)
        self._web_processor.processing_failed.connect(self.handle_processing_failed)
        self._web_processor.start()

    def handle_processing_progress(self, message: str):
        """Handle processing progress updates"""
        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage(message)

    def handle_processing_completed(self, result: WebScrapingResult):
        """Handle successful scraping"""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        self._current_result = result

        # Populate raw content
        output = []
        output.append(f"URL: {result.url}")
        output.append(f"Title: {result.title}")
        output.append(f"Method: {result.method_used}")
        output.append(f"Quality: {result.extraction_quality}")
        output.append(f"Word Count: {result.word_count}")
        output.append("=" * 80)
        output.append("")
        output.append(result.content)

        self.raw_text_edit.setText("\n".join(output))

        # Update metadata with extracted title
        if result.title and not self.metadata_panel.title_input.text().strip():
            self.metadata_panel.title_input.setText(result.title)

        # Enable next steps
        self.summarize_btn.setEnabled(True)

        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage(
                f"Extraction complete: {result.word_count} words, quality: {result.extraction_quality}"
            )

        # Auto-summarize if enabled
        if self.auto_summarize.isChecked():
            self.parent.summarize_text('web')

    def handle_processing_failed(self, error: str):
        """Handle scraping failure"""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)

        # Regular error handling
        self.raw_text_edit.setText(f"Scraping failed:\n\n{error}")

        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage("Web scraping failed")

        QMessageBox.warning(self, "Scraping Error", f"Failed to scrape page:\n\n{error}")

    def reset_fields(self):
        """Reset all fields and content"""
        self.url_input.clear()
        self.raw_text_edit.clear()
        self.summary_text_edit.clear()
        self.markdown_edit.clear()

        self.process_btn.setEnabled(False)
        self.summarize_btn.setEnabled(False)
        self.generate_markdown_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

        self.tab_widget.setCurrentIndex(0)
        self._current_result = None

        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar().showMessage("Web scraping mode reset - ready for new content")
