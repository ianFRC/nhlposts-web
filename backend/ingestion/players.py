"""PlayerResolver — fetch rosters and resolve player names."""

from __future__ import annotations

import logging
from typing import Any

from api.client import NHLClient, NotFoundError
from api.endpoints import NHLEndpoints
from db.postgres import PostgresStore
from models.player import Player, _POSITION_GROUP
from ingestion.season import ALL_TEAMS

logger = logging.getLogger(__name__)

_POSITION_SECTIONS = ("forwards", "defensemen", "goalies")


def _position_group(section: str) -> str:
    if section == "forwards":
        return "F"
    if section == "defensemen":
        return "D"
    return "G"


def _parse_roster(
    data: dict[str, Any],
    team_abbrev: str,
    team_id: int,
) -> list[Player]:
    players: list[Player] = []
    for section in _POSITION_SECTIONS:
        group = _position_group(section)
        for entry in data.get(section, []):
            try:
                pid = entry["id"]
                first = entry.get("firstName", {}).get("default", "")
                last = entry.get("lastName", {}).get("default", "")
                pos = entry.get("positionCode", group[0])
                shoots = entry.get("shootsCatches", "")
                players.append(
                    Player(
                        player_id=pid,
                        first_name=first,
                        last_name=last,
                        position_code=pos,
                        position_group=group,
                        team_abbrev=team_abbrev,
                        team_id=team_id,
                        shoots=shoots,
                    )
                )
            except (KeyError, TypeError) as exc:
                logger.debug("Skipping roster entry: %s (%s)", entry, exc)
    return players


class PlayerResolver:
    """Fetches team rosters and provides player name lookup."""

    def __init__(self, store: PostgresStore, client: NHLClient) -> None:
        self._store = store
        self._ep = NHLEndpoints(client)
        self._name_cache: dict[int, Player] | None = None

    def fetch_all_rosters(self, season: str) -> int:
        """Fetch rosters for all 32 teams. Returns number of players added/updated."""
        all_players: dict[int, Player] = {}

        for team in ALL_TEAMS:
            try:
                data = self._ep.get_roster(team, season)
            except NotFoundError:
                logger.debug("No roster for %s in %s", team, season)
                continue
            except Exception as exc:
                logger.warning("Error fetching roster for %s: %s", team, exc)
                continue

            team_id = 0
            players = _parse_roster(data, team, team_id)
            for p in players:
                all_players[p.player_id] = p

        self._store.upsert_players(list(all_players.values()))
        self._name_cache = None
        logger.info("Fetched %d players for season %s", len(all_players), season)
        return len(all_players)

    def _load_name_cache(self) -> dict[int, Player]:
        if self._name_cache is None:
            rows = self._store.get_all_players()
            self._name_cache = {
                r["player_id"]: Player(
                    player_id=r["player_id"],
                    first_name=r["first_name"],
                    last_name=r["last_name"],
                    position_code=r["position_code"],
                    position_group=r["position_group"],
                    team_abbrev=r["team_abbrev"],
                    team_id=r["team_id"],
                    shoots=r["shoots"],
                )
                for r in rows
            }
        return self._name_cache

    def get_player(self, player_id: int) -> Player | None:
        cache = self._load_name_cache()
        return cache.get(player_id)

    def resolve_name(self, name: str, threshold: int = 70) -> list[Player]:
        try:
            from rapidfuzz import process, fuzz
        except ImportError:
            logger.warning("rapidfuzz not installed; falling back to exact match")
            return self._exact_match(name)

        cache = self._load_name_cache()
        choices = {pid: p.full_name for pid, p in cache.items()}

        results = process.extract(
            name,
            choices,
            scorer=fuzz.WRatio,
            limit=10,
            score_cutoff=threshold,
        )

        players = []
        for _match_str, score, pid in results:
            p = cache.get(pid)
            if p:
                players.append((score, p))

        players.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in players]

    def _exact_match(self, name: str) -> list[Player]:
        cache = self._load_name_cache()
        name_lower = name.lower()
        return [p for p in cache.values() if name_lower in p.full_name.lower()]

    def fetch_games_played_for_players(
        self,
        player_season_pairs: list[tuple[int, str]],
        game_type: int = 2,
        progress_callback=None,
        force: bool = False,
    ) -> int:
        fetched = 0
        total = len(player_season_pairs)
        for i, (player_id, season) in enumerate(player_season_pairs):
            if not force and self._store.is_player_gp_fetched(player_id, season, game_type):
                if progress_callback:
                    progress_callback(i + 1, total)
                continue
            try:
                data = self._ep.get_player_game_log(player_id, season, game_type)
                games = data.get("gameLog", [])
                rows = [
                    (player_id, g["gameId"], g["gameDate"], season, game_type,
                     int(g.get("shots", 0)), int(g.get("goals", 0)))
                    for g in games
                    if "gameId" in g and "gameDate" in g
                ]
                self._store.bulk_upsert_player_game_log(rows)
                self._store.mark_player_gp_fetched(player_id, season, game_type)
                fetched += 1
            except Exception as exc:
                logger.warning(
                    "Could not fetch game log for player %d season %s: %s",
                    player_id, season, exc,
                )
            if progress_callback:
                progress_callback(i + 1, total)
        return fetched

    def resolve_unknown_players(self, season: str | None = None) -> int:
        unknown = self._store.get_unresolved_player_ids(season)
        if not unknown:
            return 0

        resolved = 0
        for pid in unknown:
            if self.ensure_player_known(pid, season or ""):
                resolved += 1

        if resolved:
            self._name_cache = None

        return resolved

    def ensure_player_known(self, player_id: int, season: str) -> Player | None:
        if self.get_player(player_id):
            return self.get_player(player_id)

        try:
            raw = self._ep.get_player_landing(player_id)
        except Exception as exc:
            logger.warning("Could not fetch player %d: %s", player_id, exc)
            return None

        try:
            first = raw.get("firstName", {}).get("default", "")
            last = raw.get("lastName", {}).get("default", "")
            pos = raw.get("position", "")
            shoots = raw.get("shootsCatches", "")
            group = _POSITION_GROUP.get(pos.upper(), "F")
            team_info = raw.get("currentTeamAbbrev", "")

            player = Player(
                player_id=player_id,
                first_name=first,
                last_name=last,
                position_code=pos,
                position_group=group,
                team_abbrev=team_info,
                team_id=raw.get("currentTeamId", 0),
                shoots=shoots,
            )
            self._store.upsert_player(player)
            self._name_cache = None
            return player
        except Exception as exc:
            logger.warning("Could not parse player %d landing: %s", player_id, exc)
            return None
