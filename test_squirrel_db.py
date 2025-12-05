import shutil
import subprocess
import os
import sys
import time
import http.client
import json
import urllib.parse
import pytest


def describe_squirrel_server():

    @pytest.fixture(autouse=True)
    def reset_database():
        shutil.copyfile("empty_squirrel_db.db", "squirrel_db.db")
        yield
        if os.path.exists("squirrel_db.db"):
            os.remove("squirrel_db.db")

    @pytest.fixture(autouse=True, scope="session")
    def start_and_stop_server():
        proc = subprocess.Popen([sys.executable, "squirrel_server.py"])

        for _ in range(50):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", 8080, timeout=0.2)
                conn.request("GET", "/")
                conn.getresponse()
                conn.close()
                break
            except (ConnectionRefusedError, OSError):
                time.sleep(0.1)
        else:
            proc.kill()
            pytest.fail("Squirrel server did not start on 127.0.0.1:8080")

        yield
        proc.kill()

    @pytest.fixture
    def http_client():
        conn = http.client.HTTPConnection("127.0.0.1", 8080)
        yield conn
        conn.close()

    @pytest.fixture
    def request_headers():
        return {"Content-Type": "application/x-www-form-urlencoded"}

    @pytest.fixture
    def make_squirrel(http_client, request_headers):
        body = urllib.parse.urlencode({"name": "Fred", "size": "small"})
        http_client.request("POST", "/squirrels", body=body, headers=request_headers)
        response = http_client.getresponse()
        assert response.status == 201

        http_client.request("GET", "/squirrels")
        response = http_client.getresponse()
        squirrels = json.loads(response.read())
        squirrel = squirrels[0]
        return squirrel["id"]

    def describe_get_squirrels():

        def it_returns_200_and_json_when_empty(http_client):
            http_client.request("GET", "/squirrels")
            response = http_client.getresponse()
            body = response.read()
            assert response.status == 200
            assert response.getheader("Content-Type") == "application/json"
            assert json.loads(body) == []

        def it_returns_list_with_existing_squirrel(http_client, request_headers):
            body = urllib.parse.urlencode({"name": "Fluffy", "size": "large"})
            http_client.request("POST", "/squirrels", body=body, headers=request_headers)
            post_response = http_client.getresponse()
            assert post_response.status == 201

            http_client.request("GET", "/squirrels")
            response = http_client.getresponse()
            squirrels = json.loads(response.read())
            assert len(squirrels) == 1
            assert squirrels[0]["name"] == "Fluffy"
            assert squirrels[0]["size"] == "large"

    def describe_get_single_squirrel():

        def it_returns_single_record_for_existing_id(http_client, make_squirrel):
            squirrel_id = make_squirrel
            http_client.request("GET", f"/squirrels/{squirrel_id}")
            response = http_client.getresponse()
            body = json.loads(response.read())
            assert response.status == 200
            assert response.getheader("Content-Type") == "application/json"
            assert body["id"] == squirrel_id
            assert body["name"] == "Fred"
            assert body["size"] == "small"

    def describe_create_squirrel():

        def it_returns_201_and_persists_record(http_client, request_headers):
            body = urllib.parse.urlencode({"name": "Sam", "size": "large"})
            http_client.request("POST", "/squirrels", body=body, headers=request_headers)
            response = http_client.getresponse()
            assert response.status == 201

            http_client.request("GET", "/squirrels")
            get_response = http_client.getresponse()
            squirrels = json.loads(get_response.read())
            assert len(squirrels) == 1
            created = squirrels[0]
            assert created["name"] == "Sam"
            assert created["size"] == "large"

    def describe_update_squirrel():

        def it_updates_existing_squirrel_and_returns_204(http_client, request_headers, make_squirrel):
            squirrel_id = make_squirrel
            body = urllib.parse.urlencode({"name": "Updated", "size": "tiny"})
            http_client.request(
                "PUT",
                f"/squirrels/{squirrel_id}",
                body=body,
                headers=request_headers,
            )
            response = http_client.getresponse()
            assert response.status == 204

            http_client.request("GET", f"/squirrels/{squirrel_id}")
            get_response = http_client.getresponse()
            data = json.loads(get_response.read())
            assert data["name"] == "Updated"
            assert data["size"] == "tiny"

    def describe_delete_squirrel():

        def it_deletes_existing_squirrel_and_returns_204(http_client, make_squirrel):
            squirrel_id = make_squirrel
            http_client.request("DELETE", f"/squirrels/{squirrel_id}")
            response = http_client.getresponse()
            assert response.status == 204

            http_client.request("GET", f"/squirrels/{squirrel_id}")
            get_response = http_client.getresponse()
            assert get_response.status == 404

            http_client.request("GET", "/squirrels")
            index_response = http_client.getresponse()
            squirrels = json.loads(index_response.read())
            assert squirrels == []

    def describe_failure_conditions():

        def it_returns_404_for_root_path(http_client):
            http_client.request("GET", "/")
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_unknown_collection(http_client):
            http_client.request("GET", "/squirrel")
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_nonexistent_id_on_get(http_client):
            http_client.request("GET", "/squirrels/999")
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_non_numeric_id_on_get(http_client):
            http_client.request("GET", "/squirrels/abc")
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_post_with_id(http_client, request_headers):
            body = urllib.parse.urlencode({"name": "X", "size": "small"})
            http_client.request("POST", "/squirrels/1", body=body, headers=request_headers)
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_post_to_unknown_resource(http_client, request_headers):
            body = urllib.parse.urlencode({"name": "X", "size": "small"})
            http_client.request("POST", "/chipmunks", body=body, headers=request_headers)
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_put_without_id(http_client, request_headers):
            body = urllib.parse.urlencode({"name": "X", "size": "small"})
            http_client.request("PUT", "/squirrels", body=body, headers=request_headers)
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_put_on_unknown_resource(http_client, request_headers):
            body = urllib.parse.urlencode({"name": "X", "size": "small"})
            http_client.request("PUT", "/chipmunks/1", body=body, headers=request_headers)
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_delete_without_id(http_client):
            http_client.request("DELETE", "/squirrels")
            response = http_client.getresponse()
            assert response.status == 404

        def it_returns_404_for_delete_on_unknown_resource(http_client):
            http_client.request("DELETE", "/chipmunks/1")
            response = http_client.getresponse()
            assert response.status == 404

        def it_sets_plain_text_body_for_404(http_client):
            http_client.request("GET", "/nope")
            response = http_client.getresponse()
            body = response.read().decode("utf-8")
            assert response.status == 404
            assert response.getheader("Content-Type") == "text/plain"
            assert body == "404 Not Found"
