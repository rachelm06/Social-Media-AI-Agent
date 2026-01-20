"""
Notion Client for fetching BiteRate company information and reviews.
"""
import os
from typing import List, Dict, Any, Optional
from notion_client import Client
from src.models import Review


class NotionClient:
    """Client for interacting with Notion API to fetch BiteRate content."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Notion client.
        
        Args:
            api_key: Notion API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY", "")
        if not self.api_key:
            raise ValueError("Notion API key is required. Set NOTION_API_KEY in .env file.")
        
        self.client = Client(auth=self.api_key)
    
    def get_page_content(self, page_id: str) -> str:
        """
        Fetch and extract text content from a Notion page.
        
        Args:
            page_id: The Notion page ID
            
        Returns:
            Extracted text content from the page
        """
        try:
            # Format page_id with hyphens if needed (Notion API requires this format)
            if len(page_id) == 32 and '-' not in page_id:
                formatted_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            else:
                formatted_id = page_id
            
            # First retrieve the page to verify access
            try:
                page = self.client.pages.retrieve(page_id=formatted_id)
            except Exception as page_error:
                print(f"Error accessing page {page_id}: {page_error}")
                raise
            
            # Now get the blocks
            blocks_response = self.client.blocks.children.list(block_id=formatted_id)
            
            content = []
            # Blocks response is a dict
            results = blocks_response.get("results", [])
            
            for block in results:
                text = self._extract_text_from_block(block)
                if text:
                    content.append(text)
            
            return "\n\n".join(content)
        except Exception as e:
            print(f"Error fetching page {page_id}: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def get_database_entries(self, database_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch entries from a Notion database.
        
        Args:
            database_id: The Notion database ID
            max_results: Maximum number of entries to fetch
            
        Returns:
            List of database entries with their properties
        """
        try:
            # Format database_id with hyphens (Notion API requires this format)
            # Convert from 32-char string to hyphenated format
            if len(database_id) == 32 and '-' not in database_id:
                formatted_id = f"{database_id[:8]}-{database_id[8:12]}-{database_id[12:16]}-{database_id[16:20]}-{database_id[20:]}"
            else:
                formatted_id = database_id
            
            # First verify it's actually a database
            try:
                db_info = self.client.databases.retrieve(database_id=formatted_id)
            except Exception as db_check_error:
                error_msg = str(db_check_error)
                if "page" in error_msg.lower() or "not a database" in error_msg.lower():
                    print(f"Warning: ID {database_id} appears to be a page, not a database. Skipping database query.")
                    return []
                raise
            
            # Use direct API request - make POST request to query endpoint
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            url = f"https://api.notion.com/v1/databases/{formatted_id}/query"
            
            response = httpx.post(
                url,
                headers=headers,
                json={"page_size": max_results},
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_data = response.text
                print(f"API Error Response: {error_data}")
                print(f"Status Code: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            entries = []
            pages = data.get("results", [])
            
            for page in pages[:max_results]:
                if isinstance(page, dict):
                    entry = {
                        "id": page.get("id"),
                        "properties": self._extract_properties(page.get("properties", {}))
                    }
                    entries.append(entry)
            
            return entries
        except Exception as e:
            print(f"Error fetching database {database_id}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_reviews(self, database_id: str, max_reviews: int = 10) -> List[Review]:
        """
        Fetch food reviews from a Notion database.
        
        Args:
            database_id: The Notion database ID containing reviews
            max_reviews: Maximum number of reviews to fetch
            
        Returns:
            List of Review Pydantic models
        """
        entries = self.get_database_entries(database_id, max_reviews)
        reviews = []
        
        for entry in entries:
            props = entry.get("properties", {})
            try:
                review = Review(
                    id=entry.get("id", ""),
                    restaurant=self._get_property_value(props, "Restaurant", "title") or "Unknown Restaurant",
                    rating=self._get_property_value(props, "Rating", "number"),
                    review=self._get_property_value(props, "Review", "rich_text"),
                    cuisine=self._get_property_value(props, "Cuisine", "select"),
                    location=self._get_property_value(props, "Location", "rich_text"),
                )
                reviews.append(review)
            except Exception as e:
                print(f"Error parsing review {entry.get('id')}: {e}")
                continue
        
        return reviews
    
    def get_company_info(self, page_id: str) -> str:
        """
        Fetch company information from a Notion page.
        
        Args:
            page_id: The Notion page ID containing company info
            
        Returns:
            Company information as text
        """
        return self.get_page_content(page_id)
    
    def _extract_text_from_block(self, block: Dict[str, Any]) -> str:
        """Extract text content from a Notion block."""
        # Handle both dict and object responses
        if isinstance(block, dict):
            block_type = block.get("type")
            block_data = block
        else:
            block_type = getattr(block, "type", None)
            block_data = block.__dict__ if hasattr(block, "__dict__") else {}
            # Try to get block as dict
            try:
                block_data = dict(block) if hasattr(block, "__iter__") else block_data
            except:
                pass
        
        # Get the content based on block type
        if block_type == "paragraph":
            if isinstance(block, dict):
                rich_text = block.get("paragraph", {}).get("rich_text", [])
            else:
                para = getattr(block, "paragraph", None)
                rich_text = getattr(para, "rich_text", []) if para else []
            return "".join([text.get("plain_text", "") if isinstance(text, dict) else getattr(text, "plain_text", "") for text in rich_text])
        elif block_type == "heading_1":
            if isinstance(block, dict):
                rich_text = block.get("heading_1", {}).get("rich_text", [])
            else:
                h1 = getattr(block, "heading_1", None)
                rich_text = getattr(h1, "rich_text", []) if h1 else []
            return "".join([text.get("plain_text", "") if isinstance(text, dict) else getattr(text, "plain_text", "") for text in rich_text])
        elif block_type == "heading_2":
            if isinstance(block, dict):
                rich_text = block.get("heading_2", {}).get("rich_text", [])
            else:
                h2 = getattr(block, "heading_2", None)
                rich_text = getattr(h2, "rich_text", []) if h2 else []
            return "".join([text.get("plain_text", "") if isinstance(text, dict) else getattr(text, "plain_text", "") for text in rich_text])
        elif block_type == "heading_3":
            if isinstance(block, dict):
                rich_text = block.get("heading_3", {}).get("rich_text", [])
            else:
                h3 = getattr(block, "heading_3", None)
                rich_text = getattr(h3, "rich_text", []) if h3 else []
            return "".join([text.get("plain_text", "") if isinstance(text, dict) else getattr(text, "plain_text", "") for text in rich_text])
        elif block_type == "bulleted_list_item":
            if isinstance(block, dict):
                rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
            else:
                bli = getattr(block, "bulleted_list_item", None)
                rich_text = getattr(bli, "rich_text", []) if bli else []
            return "".join([text.get("plain_text", "") if isinstance(text, dict) else getattr(text, "plain_text", "") for text in rich_text])
        elif block_type == "numbered_list_item":
            if isinstance(block, dict):
                rich_text = block.get("numbered_list_item", {}).get("rich_text", [])
            else:
                nli = getattr(block, "numbered_list_item", None)
                rich_text = getattr(nli, "rich_text", []) if nli else []
            return "".join([text.get("plain_text", "") if isinstance(text, dict) else getattr(text, "plain_text", "") for text in rich_text])
        elif block_type == "child_page":
            # Child pages don't have text content directly
            return ""
        return ""
    
    def _extract_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and simplify property values."""
        extracted = {}
        for key, prop in properties.items():
            prop_type = prop.get("type")
            extracted[key] = {
                "type": prop_type,
                "value": self._get_property_value({key: prop}, key, prop_type)
            }
        return extracted
    
    def _get_property_value(self, properties: Dict[str, Any], key: str, prop_type: str) -> Any:
        """Get value from a Notion property based on its type."""
        prop = properties.get(key, {})
        
        if prop_type == "title":
            title = prop.get("title", [])
            return "".join([t.get("plain_text", "") for t in title]) if title else ""
        elif prop_type == "rich_text":
            rich_text = prop.get("rich_text", [])
            return "".join([t.get("plain_text", "") for t in rich_text]) if rich_text else ""
        elif prop_type == "number":
            return prop.get("number")
        elif prop_type == "select":
            select = prop.get("select")
            return select.get("name") if select else None
        elif prop_type == "multi_select":
            multi_select = prop.get("multi_select", [])
            return [item.get("name") for item in multi_select]
        elif prop_type == "date":
            date = prop.get("date")
            return date.get("start") if date else None
        elif prop_type == "checkbox":
            return prop.get("checkbox", False)
        else:
            return None
