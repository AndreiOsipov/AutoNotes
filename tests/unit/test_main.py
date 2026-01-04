def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_process_video(client, sample_video):
    response = client.post("/process/", json=sample_video)

    assert response.status_code == 200
    assert isinstance(response.json(), int)
