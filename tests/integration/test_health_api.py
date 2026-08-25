from httpx import AsyncClient


async def test_liveness(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readiness(client: AsyncClient) -> None:
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
