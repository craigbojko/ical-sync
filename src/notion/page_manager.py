# -*- coding: utf-8 -*-

import sys
from notion_client import Client


class NotionPageManager:
    """
    Class to design and create our main page in Notion.
    """

    def __init__(self, notion: Client, page_id: str):
        self.notion = notion
        self.page_id = page_id

    def insert_content(self, content: str):
        """
        Insert content into the main page.
        """
        try:

            new_paragraph = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content,
                            },
                            # you can optionally set annotations here, e.g. bold/italic
                            # "annotations": {"bold": True}
                        }
                    ]
                },
            }

            # Append the block to the page
            response = self.notion.blocks.children.append(
                block_id=self.page_id, children=[new_paragraph]
            )
            
            print("Main page content inserted successfully.")
            return response
        except Exception as e:
            print(f"Error inserting content: {e}", file=sys.stderr)
            raise e
