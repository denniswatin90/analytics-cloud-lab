from unittest.mock import MagicMock

from analytics_cloud_lab.api_client import PaginatedAPIClient


def _resp(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_iter_items_follows_next_links():
    session = MagicMock()
    session.headers = {}
    session.get.side_effect = [
        _resp({"items": [{"id": 1}, {"id": 2}], "next": "https://api.example.com/x?cursor=2"}),
        _resp({"items": [{"id": 3}], "next": None}),
    ]
    client = PaginatedAPIClient("https://api.example.com", token="t", session=session)
    assert [i["id"] for i in client.iter_items("/x", params={"limit": 2})] == [1, 2, 3]
    first_call, second_call = session.get.call_args_list
    assert first_call.args[0] == "https://api.example.com/x"
    assert first_call.kwargs["params"] == {"limit": 2}
    assert second_call.args[0] == "https://api.example.com/x?cursor=2"
    assert second_call.kwargs["params"] is None
    assert session.headers["Authorization"] == "Bearer t"


def test_max_pages_stops_infinite_loops():
    session = MagicMock()
    session.headers = {}
    session.get.return_value = _resp({"items": [{"id": 1}], "next": "/again"})
    client = PaginatedAPIClient("https://api.example.com", session=session)
    assert len(list(client.iter_items("/again", max_pages=3))) == 3
