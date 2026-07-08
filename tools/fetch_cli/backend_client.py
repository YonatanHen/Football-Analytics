import requests


class BackendClient:
    """Thin HTTP client for the backend's Sofascore-facing endpoints.

    The CLI never talks to Sofascore/ScraperFC itself — only the backend
    (running with Chrome, inside Docker) does that.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_competitions(self) -> list[str]:
        resp = requests.get(f"{self.base_url}/v1/fetch/competitions", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_seasons(self, competition: str) -> dict[str, int]:
        resp = requests.get(
            f"{self.base_url}/v1/fetch/seasons",
            params={"competition": competition},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_fetched_leagues(self) -> list[dict]:
        resp = requests.get(f"{self.base_url}/v1/fetch/fetched", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def trigger_fetch(self, season: str, competition: str) -> dict:
        resp = requests.post(
            f"{self.base_url}/v1/fetch/",
            json={"season": season, "competitions": [competition], "mode": "fantasy"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_fetch_job_status(self, job_id: str) -> dict:
        resp = requests.get(f"{self.base_url}/v1/fetch/status/{job_id}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
