def test_search_returns_suggestions(client):
    response = client.get("/api/v1/geocoding/search", params={"query": "MG Road"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["label"] == "Result for MG Road"


def test_search_requires_query(client):
    response = client.get("/api/v1/geocoding/search")
    assert response.status_code == 422
