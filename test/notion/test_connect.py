import pytest
from unittest import mock

from notion.connect import NotionDatabaseConnector


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock the environment variable for the Notion API key."""
    monkeypatch.setenv("NOTION_API_KEY", "mock_api_key")


@pytest.fixture
def mock_notion():
    return mock.Mock(
        spec=NotionDatabaseConnector,
        **{
            "options": mock.Mock(auth="mock_api_key"),
            # "__query_for_connected_page": mock.Mock(),
            # "__get_driver_database_id": mock.Mock(),
        }
    )


@pytest.fixture
def connect_instance(mock_notion):
    return NotionDatabaseConnector(mock_notion)


@pytest.mark.notion
class TestConnect:
    """Test class for the NotionDatabaseConnector class."""

    def test_instantiate_connect(self, connect_instance, mock_notion):
        """Test the instantiation of the Connect class."""
        assert isinstance(connect_instance, NotionDatabaseConnector)
        assert connect_instance.notion == mock_notion

    def test_get_driver_database(self, connect_instance):
        """Test the get_driver_database method."""
        connect_instance._NotionDatabaseConnector__query_for_connected_page = mock.Mock(
            return_value="mock_page_id"
        )
        connect_instance._NotionDatabaseConnector__get_driver_database_id = mock.Mock(
            return_value="mock_database_id"
        )
        result = connect_instance.get_driver_database()
        assert result == {
            "page_id": "mock_page_id",
            "database_id": "mock_database_id",
            "database_name": "Calendar Sync - Driver Database",
            "page_name": "Calendar Sync",
        }

    def test_get_driver_database_no_page(self, connect_instance):
        """Test the get_driver_database method when no page is found."""
        connect_instance._NotionDatabaseConnector__query_for_connected_page = mock.Mock(
            return_value=None
        )
        result = connect_instance.get_driver_database()
        assert result is None

    def test_get_driver_database_with_exception(self, connect_instance):
        """Test the get_driver_database method when an exception is raised."""
        connect_instance._NotionDatabaseConnector__query_for_connected_page = mock.Mock(
            side_effect=Exception("Mocked exception")
        )
        result = connect_instance.get_driver_database()
        assert result is None

    @pytest.mark.skip(reason="Mocking example, skip for now")
    @pytest.mark.parametrize("input_value,expected", [(1, 2), (2, 3)])
    def test_example_parametrized(self, input_value, expected):
        """Example parametrized test."""
        assert input_value + 1 == expected
