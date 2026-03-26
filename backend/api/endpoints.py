"""Typed wrappers around NHL API endpoints."""

from __future__ import annotations

from typing import Any

from .client import NHLClient


class NHLEndpoints:
    """Typed endpoint helpers."""

    def __init__(self, client: NHLClient) -> None:
        self._c = client

    def get_play_by_play(self, game_id: int) -> dict[str, Any]:
        return self._c.get(f"/gamecenter/{game_id}/play-by-play")

    def get_schedule_for_date(self, date: str) -> dict[str, Any]:
        return self._c.get(f"/schedule/{date}")

    def get_team_season_schedule(self, team_abbrev: str, season: str) -> dict[str, Any]:
        return self._c.get(f"/club-schedule-season/{team_abbrev}/{season}")

    def get_roster(self, team_abbrev: str, season: str) -> dict[str, Any]:
        return self._c.get(f"/roster/{team_abbrev}/{season}")

    def get_player_landing(self, player_id: int) -> dict[str, Any]:
        return self._c.get(f"/player/{player_id}/landing")

    def get_player_game_log(
        self, player_id: int, season: str, game_type: int = 2
    ) -> dict[str, Any]:
        return self._c.get(f"/player/{player_id}/game-log/{season}/{game_type}")

    def get_schedule_now(self) -> dict[str, Any]:
        return self._c.get("/schedule/now")
