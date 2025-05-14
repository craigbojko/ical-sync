# -*- coding: utf-8 -*-

import sys
from typing import TypedDict
from loadotenv import load_env
from notion_client import Client


class DriverSyncItem(TypedDict):
    """
    Class to represent a sync item for the driver.
    """

    uid = str
    identifier = str
    ical_url = str
    enabled = bool
    database_id = str


class NotionDatabaseDriver:
    """
    Class to interact with Notion's API for driving calendar sync.
    """

    def __init__(self, notion: Client, page_id: str, database_id: str):
        self.notion = notion
        self.page_id = page_id
        self.database_id = database_id

    def get_sync_items(self):
        """
        Get sync items from the Notion database.
        """
        try:
            response = self.notion.databases.query(database_id=self.database_id)
            return response.get("results", [])
        except Exception as e:
            print(f"Error fetching sync items: {e}", file=sys.stderr)
            raise e

    def sync_items(self, items: list):
        """
        Sync items to the Notion database.
        """
        formatted_items = self.__resolve_sync_items_from_notion_db(items)
        new_databases_to_create = []
        databases_to_sync = []
        new_setup = False

        for item in formatted_items:
            has_database_id = item.get("database_id").get("rich_text", [])
            if len(has_database_id) > 0:
                databases_to_sync.append(item)
            else:
                new_databases_to_create.append(item)

        if len(new_databases_to_create) > 0 and len(databases_to_sync) == 0:
            print("New setup detected. Adding database ID column to driver database.")
            new_setup = True
            print("Database ID column added to driver database.")

        if len(new_databases_to_create) > 0:
            print(f"Creating new databases: {new_databases_to_create}")
            new_items = self.__create_databases_for_new_items(new_databases_to_create)
            databases_to_sync.extend(new_items)

            if new_setup:
                self.__add_database_id_column()

            for item in new_items:
                self.__update_driver_item_with_database_id(item)
                print(
                    f"Updated driver item with database ID: {item['database_id']}"
                )

            print(f"New databases created: {new_items}")
        else:
            print("No new databases to create.")

        if len(databases_to_sync) > 0:
            print(f"Syncing existing databases: {databases_to_sync}")
            # Logic to sync existing databases
        else:
            print("No existing databases to sync.")

    def __create_databases_for_new_items(
        self, items: list[DriverSyncItem]
    ) -> list[DriverSyncItem]:
        """
        Create new databases for the given items.
        """
        for item in items:
            try:
                database_create_response = self.__create_database(item)
                item["database_id"] = database_create_response.get("id")

            except Exception as e:
                print(f"Error creating database for item {item}: {e}", file=sys.stderr)
                raise e
        print(f"Created databases for items: {items}")
        return items

    def __create_database(self, item: DriverSyncItem):
        """
        Create a new database in Notion.
        """
        try:
            response = self.notion.databases.create(
                parent={"type": "page_id", "page_id": self.page_id},
                title=[{"type": "text", "text": {"content": item["identifier"]}}],
                properties={
                    "Name": {"title": {}},
                    "Due Date": {"date": {}},
                    "EventUID": {"rich_text": {}},
                    "InstanceUID": {"rich_text": {}},
                },
            )
            return response
        except Exception as e:
            print(f"Error creating database: {e}", file=sys.stderr)
            raise e

    def __add_database_id_column(self):
        """
        Add a new column to the driver database for the database ID.
        """
        try:
            self.notion.databases.update(
                database_id=self.database_id,
                properties={
                    "Database ID": {
                        "rich_text": {},
                    }
                },
            )
        except Exception as e:
            print(f"Error adding database ID column: {e}", file=sys.stderr)
            raise e

    def __update_driver_item_with_database_id(self, item: DriverSyncItem):
        """
        Update the driver item with the database ID.
        """
        try:
            self.notion.pages.update(
                page_id=item["uid"],
                properties={
                    "Database ID": {
                        "rich_text": [{
                            "type": "text",
                            "text": {
                                "content": item["database_id"],
                            },
                        }],
                    }
                },
            )
        except Exception as e:
            print(f"Error updating driver item: {e}", file=sys.stderr)
            raise e

    def __resolve_sync_items_from_notion_db(self, items) -> list[DriverSyncItem]:
        """
        Process and return sync items as a dictionary.
        """
        return [
            {
                "uid": item["id"],
                "identifier": properties.get("Identifier/Name", {})
                .get("title", [])[0]
                .get("text", {})
                .get("content"),
                "ical_url": properties.get("ICAL URL", {}).get("url"),
                "enabled": properties.get("Sync_Enabled", {}).get("checkbox"),
                "database_id": properties.get("Database ID", {}) or {},
            }
            for item in items
            if (properties := item.get("properties", {}))
            and properties.get("Identifier/Name", {}).get("title", [])
            and properties.get("ICAL URL", {}).get("url")
            # and properties.get("Database ID", {})
            and properties.get("Sync_Enabled", {}).get("checkbox")
        ]
