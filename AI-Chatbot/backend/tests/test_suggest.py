import pytest

def test_get_prompts(client):
    response = client.get("/api/suggest/prompts?count=4")
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    assert len(data["prompts"]) == 4

    response2 = client.get("/api/suggest/prompts?count=10")
    assert response2.status_code == 200
    data2 = response2.json()
    # The max is 8 as per the code
    assert len(data2["prompts"]) <= 8
