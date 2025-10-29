# website_tree_crawler.py
"""
Website Tree Crawler for Auto Tab
Iterative tree-based website exploration with cluster persistence
"""

import logging
import sqlite3
import json
import time
from typing import Optional, List, Dict, Set
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, urljoin
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


@dataclass
class TreeNode:
    """Represents a node in the website tree"""
    url: str
    title: str = ""
    parent_url: Optional[str] = None
    depth: int = 0
    is_analyzed: bool = False
    is_external: bool = False
    is_checked: bool = False
    node_type: str = "page"  # page, section, archive, external
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CrawlCluster:
    """Saved cluster of selected URLs"""
    cluster_id: Optional[int] = None
    cluster_name: str = ""
    start_url: str = ""
    selected_urls: List[str] = None
    tree_state: Dict = None  # Full tree for resume
    created_at: str = ""
    project_name: str = ""
    
    def __post_init__(self):
        if self.selected_urls is None:
            self.selected_urls = []
        if self.tree_state is None:
            self.tree_state = {}


class WebCrawlerDatabase:
    """SQLite database for cluster persistence"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()
    
    def _init_schema(self):
        """Initialize crawler tables"""
        cursor = self.conn.cursor()

        # Clusters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS web_clusters (
                cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_name TEXT NOT NULL,
                project_name TEXT,
                start_url TEXT NOT NULL,
                selected_urls TEXT,  -- JSON array
                tree_state TEXT,     -- JSON serialized tree
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tree nodes table (for detailed state preservation)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tree_nodes (
                node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                parent_url TEXT,
                depth INTEGER DEFAULT 0,
                is_analyzed BOOLEAN DEFAULT 0,
                is_external BOOLEAN DEFAULT 0,
                is_checked BOOLEAN DEFAULT 0,
                node_type TEXT DEFAULT 'page',
                metadata TEXT, -- JSON
                FOREIGN KEY (cluster_id) REFERENCES web_clusters (cluster_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster ON tree_nodes(cluster_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON tree_nodes(url)")
        
        self.conn.commit()
    
    def save_cluster(self, cluster: CrawlCluster) -> int:
        """Save or update cluster"""
        cursor = self.conn.cursor()
        
        selected_urls_json = json.dumps(cluster.selected_urls)
        tree_state_json = json.dumps(cluster.tree_state)
        
        if cluster.cluster_id is None:
            # Insert new
            cursor.execute("""
                INSERT INTO web_clusters 
                (cluster_name, project_name, start_url, selected_urls, tree_state)
                VALUES (?, ?, ?, ?, ?)
            """, (
                cluster.cluster_name,
                cluster.project_name,
                cluster.start_url,
                selected_urls_json,
                tree_state_json
            ))
            cluster_id = cursor.lastrowid
        else:
            # Update existing
            cursor.execute("""
                UPDATE web_clusters 
                SET cluster_name = ?, selected_urls = ?, tree_state = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """, (
                cluster.cluster_name,
                selected_urls_json,
                tree_state_json,
                cluster.cluster_id
            ))
            cluster_id = cluster.cluster_id
        
        self.conn.commit()
        return cluster_id
    
    def load_cluster(self, cluster_id: int) -> Optional[CrawlCluster]:
        """Load cluster by ID"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT cluster_id, cluster_name, project_name, start_url, 
                   selected_urls, tree_state, created_at
            FROM web_clusters WHERE cluster_id = ?
        """, (cluster_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return CrawlCluster(
            cluster_id=row[0],
            cluster_name=row[1],
            project_name=row[2],
            start_url=row[3],
            selected_urls=json.loads(row[4]),
            tree_state=json.loads(row[5]),
            created_at=row[6]
        )
    
    def list_clusters(self, project_name: Optional[str] = None) -> List[Dict]:
        """List all clusters, optionally filtered by project"""
        cursor = self.conn.cursor()
        
        if project_name:
            cursor.execute("""
                SELECT cluster_id, cluster_name, start_url, created_at,
                       json_array_length(selected_urls) as url_count
                FROM web_clusters 
                WHERE project_name = ?
                ORDER BY updated_at DESC
            """, (project_name,))
        else:
            cursor.execute("""
                           SELECT cluster_id,cluster_name,start_url,created_at,
                                  json_array_length(selected_urls) as url_count
                           FROM web_clusters
                           ORDER BY updated_at DESC
            """)
        
        rows = cursor.fetchall()
        return [
            {
                "cluster_id": row[0],
                "cluster_name": row[1],
                "start_url": row[2],
                "created_at": row[3],
                "url_count": row[4] or 0
            }
            for row in rows
        ]
    
    def delete_cluster(self, cluster_id: int):
        """Delete cluster and its nodes"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM web_clusters WHERE cluster_id = ?", (cluster_id,))
        self.conn.commit()


class WebsiteTreeCrawler:
    """
    Iterative website tree crawler with per-domain rate limiting
    Supports analyze, expand, save cluster, and resume operations
    """
    
    def __init__(self, db_path: str, rate_limiter=None):
        self.db = WebCrawlerDatabase(db_path)
        self.rate_limiter = rate_limiter
        self.tree: Dict[str, TreeNode] = {}  # url -> TreeNode
        self.user_agent = "DataWoven/1.0 (Knowledge Capture Tool)"

        # Current cluster being built
        self.current_cluster: Optional[CrawlCluster] = None
    
    def analyze_start_url(self, url: str, same_domain_only: bool = True) -> Dict[str, TreeNode]:
        """
        Analyze the starting URL and return initial tree with child links
        
        Returns:
            Dict mapping URL -> TreeNode for root and immediate children
        """
        _LOGGER.info(f"Analyzing start URL: {url}")
        
        # Clear existing tree
        self.tree = {}
        
        # Create root node
        parsed_url = urlparse(url)
        root_node = TreeNode(
            url=url,
            depth=0,
            is_analyzed=False,
            node_type="page"
        )
        
        try:
            # Fetch page
            domain = parsed_url.netloc
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed(domain)
            
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            root_node.title = title_tag.get_text(strip=True) if title_tag else url
            
            # Extract description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                root_node.metadata['description'] = meta_desc.get('content', '')
            
            root_node.is_analyzed = True
            self.tree[url] = root_node
            
            # Extract child links
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                absolute_url = urljoin(url, href)
                
                # Parse child URL
                child_parsed = urlparse(absolute_url)
                
                # Skip anchors, javascript, mailto, etc.
                if child_parsed.scheme not in ['http', 'https']:
                    continue
                
                # Check if external
                is_external = child_parsed.netloc != parsed_url.netloc
                
                # Skip external if same_domain_only
                if same_domain_only and is_external:
                    continue
                
                # Skip if already in tree
                if absolute_url in self.tree:
                    continue
                
                # Determine node type
                node_type = "external" if is_external else "page"
                if any(absolute_url.endswith(ext) for ext in ['.pdf', '.zip', '.tar.gz']):
                    node_type = "archive"
                
                # Create child node
                child_node = TreeNode(
                    url=absolute_url,
                    title=link.get_text(strip=True)[:100] or absolute_url,
                    parent_url=url,
                    depth=1,
                    is_analyzed=False,
                    is_external=is_external,
                    node_type=node_type
                )
                
                self.tree[absolute_url] = child_node
            
            _LOGGER.info(f"Found {len(self.tree) - 1} child links")
            return self.tree
            
        except Exception as e:
            _LOGGER.error(f"Failed to analyze {url}: {e}")
            root_node.metadata['error'] = str(e)
            self.tree[url] = root_node
            return self.tree
    
    def expand_nodes(self, urls: List[str], same_domain_only: bool = True, max_depth: int = 5) -> Dict[str, TreeNode]:
        """
        Expand selected nodes by fetching their child links
        
        Args:
            urls: List of URLs to expand
            same_domain_only: Only follow links on same domain
            max_depth: Maximum depth to crawl
            
        Returns:
            Updated tree dict
        """
        for url in urls:
            if url not in self.tree:
                _LOGGER.warning(f"URL not in tree: {url}")
                continue
            
            node = self.tree[url]
            
            # Skip if already analyzed
            if node.is_analyzed:
                _LOGGER.info(f"Already analyzed: {url}")
                continue
            
            # Skip if at max depth
            if node.depth >= max_depth:
                _LOGGER.info(f"Max depth reached: {url}")
                continue
            
            # Skip external links
            if node.is_external:
                _LOGGER.info(f"Skipping external: {url}")
                continue
            
            try:
                # Rate limit
                parsed = urlparse(url)
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed(parsed.netloc)
                
                # Fetch page
                headers = {'User-Agent': self.user_agent}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Update title if not set
                if not node.title or node.title == url:
                    title_tag = soup.find('title')
                    node.title = title_tag.get_text(strip=True) if title_tag else url
                
                # Extract description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    node.metadata['description'] = meta_desc.get('content', '')
                
                node.is_analyzed = True
                
                # Extract child links
                links = soup.find_all('a', href=True)
                child_count = 0
                
                for link in links:
                    href = link.get('href')
                    absolute_url = urljoin(url, href)
                    
                    child_parsed = urlparse(absolute_url)
                    
                    # Skip non-HTTP
                    if child_parsed.scheme not in ['http', 'https']:
                        continue
                    
                    # Check if external
                    is_external = child_parsed.netloc != parsed.netloc
                    
                    if same_domain_only and is_external:
                        continue
                    
                    # Skip duplicates
                    if absolute_url in self.tree:
                        continue
                    
                    # Determine type
                    node_type = "external" if is_external else "page"
                    if any(absolute_url.endswith(ext) for ext in ['.pdf', '.zip', '.tar.gz']):
                        node_type = "archive"
                    
                    # Create child
                    child_node = TreeNode(
                        url=absolute_url,
                        title=link.get_text(strip=True)[:100] or absolute_url,
                        parent_url=url,
                        depth=node.depth + 1,
                        is_analyzed=False,
                        is_external=is_external,
                        node_type=node_type
                    )
                    
                    self.tree[absolute_url] = child_node
                    child_count += 1
                
                _LOGGER.info(f"Expanded {url}: found {child_count} new links")
                
            except Exception as e:
                _LOGGER.error(f"Failed to expand {url}: {e}")
                node.metadata['error'] = str(e)
                node.is_analyzed = True  # Mark as analyzed to prevent retry
        
        return self.tree
    
    def get_checked_urls(self) -> List[str]:
        """Return list of URLs that are checked"""
        return [url for url, node in self.tree.items() if node.is_checked]
    
    def set_checked_urls(self, urls: List[str]):
        """Set checked state for URLs"""
        for url in urls:
            if url in self.tree:
                self.tree[url].is_checked = True
    
    def save_cluster(self, cluster_name: str, project_name: str = "") -> int:
        """
        Save current tree as a cluster
        
        Returns:
            cluster_id
        """
        checked_urls = self.get_checked_urls()
        
        if not checked_urls:
            raise ValueError("No URLs selected to save")
        
        # Serialize tree state
        tree_state = {
            url: {
                'title': node.title,
                'parent_url': node.parent_url,
                'depth': node.depth,
                'is_analyzed': node.is_analyzed,
                'is_external': node.is_external,
                'is_checked': node.is_checked,
                'node_type': node.node_type,
                'metadata': node.metadata
            }
            for url, node in self.tree.items()
        }
        
        # Get start URL (depth 0)
        start_url = next((url for url, node in self.tree.items() if node.depth == 0), "")
        
        cluster = CrawlCluster(
            cluster_name=cluster_name,
            project_name=project_name,
            start_url=start_url,
            selected_urls=checked_urls,
            tree_state=tree_state
        )
        
        cluster_id = self.db.save_cluster(cluster)
        self.current_cluster = cluster
        self.current_cluster.cluster_id = cluster_id
        
        _LOGGER.info(f"Saved cluster '{cluster_name}' with {len(checked_urls)} URLs")
        return cluster_id
    
    def load_cluster(self, cluster_id: int):
        """Load a saved cluster and restore tree state"""
        cluster = self.db.load_cluster(cluster_id)
        
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")
        
        # Restore tree from saved state
        self.tree = {}
        for url, node_data in cluster.tree_state.items():
            node = TreeNode(
                url=url,
                title=node_data['title'],
                parent_url=node_data.get('parent_url'),
                depth=node_data['depth'],
                is_analyzed=node_data['is_analyzed'],
                is_external=node_data['is_external'],
                is_checked=node_data['is_checked'],
                node_type=node_data.get('node_type', 'page'),
                metadata=node_data.get('metadata', {})
            )
            self.tree[url] = node
        
        self.current_cluster = cluster
        _LOGGER.info(f"Loaded cluster '{cluster.cluster_name}' with {len(self.tree)} nodes")
        
        return cluster
    
    def get_tree_for_display(self) -> Dict:
        """
        Format tree for UI display
        Returns hierarchical structure
        """
        # Find root
        root_url = next((url for url, node in self.tree.items() if node.depth == 0), None)
        
        if not root_url:
            return {}
        
        def build_hierarchy(parent_url: str, max_depth: int = 10) -> Dict:
            """Recursively build tree structure"""
            parent_node = self.tree.get(parent_url)
            
            if not parent_node or parent_node.depth >= max_depth:
                return {}
            
            # Find children
            children = [
                url for url, node in self.tree.items()
                if node.parent_url == parent_url
            ]
            
            result = {
                'url': parent_url,
                'title': parent_node.title,
                'is_analyzed': parent_node.is_analyzed,
                'is_checked': parent_node.is_checked,
                'is_external': parent_node.is_external,
                'node_type': parent_node.node_type,
                'depth': parent_node.depth,
                'children': []
            }
            
            for child_url in sorted(children):
                child_tree = build_hierarchy(child_url, max_depth)
                if child_tree:
                    result['children'].append(child_tree)
            
            return result
        
        return build_hierarchy(root_url)
