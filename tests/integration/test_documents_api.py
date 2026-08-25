from httpx import AsyncClient

SAMPLE_TEXT = (
    "FastAPI is a modern web framework. It is fast to run. It is built on "
    "Starlette and Pydantic. Many teams use it in production today."
)


async def test_create_and_get_document(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/documents", json={"title": "Test", "text": SAMPLE_TEXT}, headers=auth_headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Test"
    assert body["word_count"] > 0
    assert body["sentence_count"] >= 1
    assert body["summary"]

    get_resp = await client.get(f"/documents/{body['id']}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


async def test_create_document_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/documents", json={"text": "Hello there. General Kenobi."})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_create_document_rejects_text_with_no_sentences(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post("/documents", json={"text": "   "}, headers=auth_headers)
    assert resp.status_code == 422


async def test_get_missing_document_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/documents/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_list_documents(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await client.post("/documents", json={"text": SAMPLE_TEXT}, headers=auth_headers)
    resp = await client.get("/documents", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
