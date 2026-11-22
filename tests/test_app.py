import pytest

from partsbin import create_app
from partsbin.db import get_db
from partsbin.intake import add_source, receive


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTSBIN_DB", str(tmp_path / "test.db"))
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def add_part(client, name, qty, location_id=""):
    return client.post("/part/new", data={"name": name, "category": "Sensors", "qty": qty, "location_id": location_id})


def test_add_and_list_part(client):
    add_part(client, "DHT11", 2)
    page = client.get("/").get_data(as_text=True)
    assert "DHT11" in page


def test_adjust_never_goes_negative(client):
    add_part(client, "Servo", 1)
    assert client.post("/part/1/adjust", json={"delta": -1}).get_json()["qty"] == 0
    assert client.post("/part/1/adjust", json={"delta": -1}).get_json()["qty"] == 0
    assert client.post("/part/1/adjust", json={"delta": 3}).get_json()["qty"] == 3


def test_search_filters(client):
    add_part(client, "Laser emitter", 1)
    add_part(client, "OLED", 1)
    page = client.get("/?q=laser").get_data(as_text=True)
    assert "Laser emitter" in page
    assert "OLED" not in page


def test_project_buildable_sums_across_locations(client):
    client.post("/locations", data={"name": "Box A"})
    client.post("/locations", data={"name": "Box B"})
    add_part(client, "DHT11", 1, 1)
    add_part(client, "dht11", 1, 2)
    client.post("/projects", data={"name": "Weather"})
    client.post("/project/1", data={"action": "add", "part_name": "DHT11", "qty": 2})
    page = client.get("/project/1").get_data(as_text=True)
    assert "You have everything" in page


def test_building_project_reserves_parts(client):
    add_part(client, "Servo", 1)
    client.post("/projects", data={"name": "Flag"})
    client.post("/project/1", data={"action": "add", "part_name": "Servo", "qty": 1})
    client.post("/project/1", data={"action": "update", "status": "building", "notes": ""})
    client.post("/projects", data={"name": "Second"})
    client.post("/project/2", data={"action": "add", "part_name": "Servo", "qty": 1})
    assert "Missing parts" in client.get("/project/2").get_data(as_text=True)
    assert "You have everything" in client.get("/project/1").get_data(as_text=True)


def test_location_delete_only_when_empty_in_ui(client):
    client.post("/locations", data={"name": "Drawer"})
    add_part(client, "LED", 5, 1)
    page = client.get("/locations").get_data(as_text=True)
    assert "Drawer" in page
    assert ">delete<" not in page


def test_receive_merges_by_name_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("PARTSBIN_DB", str(tmp_path / "test.db"))
    app = create_app()
    with app.app_context():
        db = get_db()
        assert receive(db, "Kit A", [("Sensors", "DHT11", 1, "temp")])
        assert receive(db, "Kit B", [("Sensors", "dht11", 2, "humidity")])
        assert not receive(db, "Kit B", [("Sensors", "DHT11", 2, "")])
        rows = db.execute("SELECT * FROM part").fetchall()
        assert len(rows) == 1
        assert rows[0]["qty"] == 3
        assert rows[0]["tags"] == "temp, humidity"
        assert rows[0]["notes"] == "from: Kit A, Kit B"


def test_add_source_keeps_user_notes():
    assert add_source("pins bent", "Kit A") == "pins bent\nfrom: Kit A"
    assert add_source("pins bent\nfrom: Kit A", "Kit A") == "pins bent\nfrom: Kit A"
