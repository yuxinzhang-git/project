import unittest

import httpx

from app.main import create_app


class StaticPageCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_exposes_current_runtime_version(self):
        app = create_app()
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "2.2.0")

    async def test_frontend_pages_are_not_cached(self):
        app = create_app()
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            for path in ("/", "/daily.html", "/sports.html"):
                response = await client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn("no-store", response.headers.get("cache-control", ""), path)


if __name__ == "__main__":
    unittest.main()
