import pytest
from unittest import mock

from notion.driver import NotionDatabaseDriver


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock the environment variable for the Notion API key."""
    monkeypatch.setenv("NOTION_API_KEY", "mock_api_key")


@pytest.fixture
def mock_notion():
    return mock.Mock(
        spec=NotionDatabaseDriver,
        **{"options": mock.Mock(auth="mock_api_key"), "databases": mock.Mock()}
    )


@pytest.fixture
def driver_instance(mock_notion):
    return NotionDatabaseDriver(mock_notion, "mock_page_id", "mock_database_id")


@pytest.mark.notion
class TestConnect:
    """Test class for the NotionDatabaseDriver class."""

    def test_instantiate_connect(self, driver_instance, mock_notion):
        """Test the instantiation of the Connect class."""
        assert isinstance(driver_instance, NotionDatabaseDriver)
        assert driver_instance.notion == mock_notion

    def test_get_sync_items(self, driver_instance):
        """Test the get_sync_items method."""
        # Arrange
        mock_response = {"results": ["item1", "item2"]}
        driver_instance.notion.databases.query = mock.Mock(return_value=mock_response)

        # Act
        result = driver_instance.get_sync_items()

        # Assert
        assert result == ["item1", "item2"]

    def test_get_sync_items_with_exception(self, driver_instance):
        """Test the get_sync_items method when an exception is raised."""
        # Arrange
        driver_instance.notion.databases.query = mock.Mock(
            side_effect=Exception("Mocked exception")
        )

        # Act
        with pytest.raises(Exception) as exc_info:
            driver_instance.get_sync_items()
        error = str(exc_info.value)

        # Assert
        assert error == "Mocked exception"
        # Ensure the exception is raised only once
        assert driver_instance.notion.databases.query.call_count == 1
