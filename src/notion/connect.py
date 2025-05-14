# -*- coding: utf-8 -*-
import sys
import re
from typing import TypedDict
from notion_client import Client

from notion.page_manager import NotionPageManager


class ConnectionDetails(TypedDict):
    """
    TypedDict to hold connection details for Notion.
    """

    page_id: str
    database_id: str
    database_name: str
    page_name: str


class NotionDatabaseConnector:
    """
    Class to connect to Notion and create or query a calendar sync database.
    """

    __NOTION_DEFAULT_PAGE_NAME = "Calendar Sync"
    __NOTION_DEFAULT_DATABASE_NAME = "Calendar Sync - Driver Database"

    def __init__(self, notion: Client):
        self.notion = notion

    def set_notion_default_database_name(self, name: str):
        """
        Set the default database name for Notion.
        """
        self.__NOTION_DEFAULT_PAGE_NAME = name
        print(f"Default database name set to: {self.__NOTION_DEFAULT_PAGE_NAME}")

    def get_driver_database(self) -> ConnectionDetails:
        """
        Get the driver database from Notion.
        """
        # Query for a connected page
        try:
            connected_page_id = self.__query_for_connected_page(
                self.__NOTION_DEFAULT_PAGE_NAME
            )
        except Exception as e:
            print(f"Error querying Notion: {e}", file=sys.stderr)
            return None

        if connected_page_id is None:
            print(
                "No connected page found. Creating a page and connect it to the integration and try again."
            )
            return None

        print(f"Connected page found with ID: {connected_page_id}")

        database_id = self.__get_driver_database_id(connected_page_id)

        return {
            "page_id": connected_page_id,
            "database_id": database_id,
            "database_name": self.__NOTION_DEFAULT_DATABASE_NAME,
            "page_name": self.__NOTION_DEFAULT_PAGE_NAME,
        }

    def __query_for_connected_page(self, default_search_string: str) -> str:
        """
        Query for a connected page in Notion to sync with the calendar.
        """
        # Query for the page
        response = self.notion.search(
            query=default_search_string,
            filter={
                "property": "object",
                "value": "page",
            },
        )

        # Check if the page exists
        if len(response["results"]) <= 0:
            # No pages found, return None
            return None

        # Find the first page containing the specified name
        for page in response["results"]:
            title = page.get("properties", {}).get("title", {})
            if not title:
                continue
            regex = re.compile(default_search_string, re.IGNORECASE)
            if title.get("title") and regex.search(
                title["title"][0]["text"]["content"]
            ):
                print(f"Found connected page: {title['title'][0]['text']['content']}")
                return page["id"]

        return None  # Return None if no page was found

    def __get_driver_database_id(self, page_id: str) -> str:
        """
        Get the driver database ID from Notion.
        """
        try:
            db_id = self.__query_for_existing_driver_database(
                self.__NOTION_DEFAULT_DATABASE_NAME
            )
        except Exception as e:
            print(f"Error querying Notion: {e}")
            return None

        if db_id:
            print(f"Found existing database with ID: {db_id}")
        else:
            print("No existing database found. Creating a new one...")
            db_id = self.__create_calendar_sync_database(
                page_id, self.__NOTION_DEFAULT_DATABASE_NAME
            )
            print(f"Created new database with ID: {db_id}")

        return db_id

    def __query_for_existing_driver_database(self, database_name: str) -> str:
        """
        Query for an existing database in Notion to sync with the calendar.
        """
        # Query for the database
        response = self.notion.search(
            query=database_name,
            filter={
                "property": "object",
                "value": "database",
            },
        )

        # Check if the database exists
        if len(response["results"]) > 0:
            # Find the first database with the specified name
            for db in response["results"]:
                if db["title"][0]["text"]["content"] == database_name:
                    print(
                        f"Found existing database: {db['title'][0]['text']['content']}"
                    )
                    return db["id"]

        return None  # Return None if no database was found

    def __create_calendar_sync_database(
        self, parent_page_id: str, database_name: str
    ) -> str:
        """
        Create a new database in Notion to sync with the calendar.
        """
        response = self.notion.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": database_name}}],
            properties={
                "Identifier/Name": {"title": {}},
                "ICAL URL": {"url": {}},
                "Sync_Enabled": {"checkbox": {}},
            },
        )

        # Add our standard content to the main page
        page_content = NotionPageManager(self.notion, parent_page_id)
        page_content.insert_content(
            "This is the main page content for the calendar sync."
        )

        return response["id"]  # Return the ID of the created database
