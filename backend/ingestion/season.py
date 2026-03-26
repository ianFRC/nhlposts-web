"""SeasonFetcher — discover all game IDs for a season or date range."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from api.client import NHLClient, NotFoundError
from api.endpoints import NHLEndpoints
from db.postgres import PostgresStore
from models.game import Game

logger = logging.getLogger(__name__)

ALL_TEAMS = [
    "ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL",
    "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD",
    "NSH", "NYI", "NYR", "OTT", "PHI", "PIT", "SEA", "SJS",
    "STL", "TBL", "TOR", "UTA", "VAN", "VGK", "WPG", "WSH",
]


def _parse_game(game_data: dict[str, Any], season: str) -> Game | None:
    try:
        game_id = game_data["id"]
        game_type = game_data.get("gameType", 2)
        game_date = game_data.get("gameDate", "")[:10]
        game_state = game_data.get("gameState", "OFF")

        home = game_data.get("homeTeam", {})
        away = game_data.get("awayTeam", {})

        return Game(
            game_id=game_id,
            season=season,
            game_type=game_type,
            game_date=game_date,
            home_team_id=home.get("id", 0),
            home_team_abbrev=home.get("abbrev", ""),
            away_team_id=away.get("id", 0),
            away_team_abbrev=away.get("abbrev", ""),
            game_state=game_state,
        )
    except (KeyError, TypeError) as exc:
        logger.debug("Could not parse game data: %s (%s)", game_data, exc)
        return None


class SeasonFetcher:
    """Discovers all game IDs for a season or date range and stores them."""

    def __init__(self, store: PostgresStore, client: NHLClient) -> None:
        self._store = store
        self._ep = NHLEndpoints(client)

    def fetch_season(self, season: str, game_type: int = 2) -> list[Game]:
        """Fetch all games for a season by querying each team's schedule."""
        logger.info("Discovering games for season %s via team schedules...", season)
        seen: dict[int, Game] = {}

        for team in ALL_TEAMS:
            try:
                data = self._ep.get_team_season_schedule(team, season)
            except NotFoundError:
                logger.debug("No schedule found for %s in season %s", team, season)
                continue
            except Exception as exc:
                logger.warning("Error fetching schedule for %s: %s", team, exc)
                continue

            games_list = data.get("games", [])
            for gd in games_list:
                if gd.get("gameType", 2) != game_type:
                    continue
                game = _parse_game(gd, season)
                if game and game.game_id not in seen:
                    seen[game.game_id] = game

        games = list(seen.values())
        logger.info("Discovered %d unique games for season %s", len(games), season)
        self._store.upsert_games(games)
        return games

    def fetch_date_range(self, date_from: str, date_to: str) -> list[Game]:
        """Fetch all games in a date range by walking the schedule endpoint."""
        logger.info("Walking schedule from %s to %s...", date_from, date_to)
        seen: dict[int, Game] = {}
        current_date = date_from

        while current_date <= date_to:
            try:
                data = self._ep.get_schedule_for_date(current_date)
            except NotFoundError:
                logger.debug("No schedule data for %s", current_date)
                d = date.fromisoformat(current_date) + timedelta(days=7)
                current_date = d.isoformat()
                continue
            except Exception as exc:
                logger.warning("Error fetching schedule for %s: %s", current_date, exc)
                d = date.fromisoformat(current_date) + timedelta(days=7)
                current_date = d.isoformat()
                continue

            for week in data.get("gameWeek", []):
                for gd in week.get("games", []):
                    gdate = gd.get("gameDate", "")[:10]
                    if gdate > date_to:
                        continue
                    gid = gd.get("id", 0)
                    season = str(gid)[:4] + str(int(str(gid)[:4]) + 1)
                    game = _parse_game(gd, season)
                    if game and game.game_id not in seen:
                        seen[game.game_id] = game

            next_date = data.get("nextStartDate")
            if next_date:
                current_date = next_date[:10]
            else:
                d = date.fromisoformat(current_date) + timedelta(days=7)
                current_date = d.isoformat()

        games = [g for g in seen.values() if date_from <= g.game_date <= date_to]
        logger.info("Discovered %d games in date range %s–%s", len(games), date_from, date_to)
        self._store.upsert_games(games)
        return games
