import time
import pandas as pd
from nba_api.stats.endpoints import (
    TeamGameLog,
    BoxScoreAdvancedV2,
    LeagueGameFinder,
    PlayerGameLog
)
from nba_api.stats.static import teams

SLEEP_SECONDS = 0.7
SEASONS = ["2021-2022", "2022-2023", "2023-2024"]

def get_all_team_game_logs(seasons=SEASONS) -> pd.DataFrame:
    """
    Acquire live data logged by NBA.com. Utilize Sleep_seconds otherwise 429-ban.
    """

    all_rows = []
    nba_teams = teams.get_teams()

    for season in seasons:
        for team in nba_teams:
            try:
                log = TeamGameLog(
                    team_id=team["id"],
                    season=season,
                    season_type_all_star="Regular Season",
                ).get_data_frames()[0]

                log["TEAM_ID"] = team["id"]
                log["TEAM_NAME"] = team["full_name"]
                log["season"] = season
                all_rows.append(log)
                time.sleep(SLEEP_SECONDS)
            except Exception as e:
                print(f"    Error on {team['full_name']}: {e}")
                time.sleep(2)
    df = pd.concat(all_rows, ignore_index=True)
    df = _clean_team_log(df)

    return df
def _clean_team_log(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts Home/Away data. Classifies with WIN/LOSS label.
    """
    df["WIN"] = (df["WIN"] == "W").astype(int)
    df["IS_HOME"] = df["MATCHUP"].apply(
        lambda x: 1 if "vs." in x else 0
    )
    df["OPP_ABB"] = df["MATCHUP"].apply(
        lambda x: x.split("vs.  ")[-1] if "vs. " in x else x.split("@ ")[-1]
    )

    df.columns = [c.upper() for c in df.columns]

    return df
def get_advanced_stats_for_games(game_ids: list) -> pd.DataFrame:
        """
        Returns advanced stats per team per game.
        game_ids: list of NBA game ID strings
        """

        all_rows = []

        for i, game_id in enumerate(game_ids):
            if i % 50:
                print(f"   Advance stats: {i}/{len(game_ids)}")
            try:
                box = BoxScoreAdvancedV2(game_id=game_id).get_data_frames()
                team_adv = box[1]
                team_adv["GAME_ID"] = game_id
                all_rows.append(team_adv)
                time.sleep(SLEEP_SECONDS)
            except Exception as e:
                print(f"    Error on game {game_id}: {e}")
                time.sleep(2)

        return pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
def build_matchup_dataset(team_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Joins home vs. away team stats into. one row per game with:
    - Home team features
    - Away team features
    - Label: HOME_WIN

    Rolling 10-game averages so each game only uses past data (no leakage).
    """
    df = team_logs.copy()

    df = df.sort_values(["TEAM_ID", "GAME_DATE"])

    stat_cols = ["PTS", "FGA", "FG_PCT", "FG3_PCT", "FT_PCT", 
                 "REB", "AST", "TOV", "STL", "BLK", "PLUS_MINUS"]
    
    for col in stat_cols:
        if col in df.columns:
            df[f"ROLL10_{col}"] = (
                df.groupby("TEAM_ID")[col]
                .transform(lambda x: x.shift(1).rolling(10, min_periods=3).mean())
            )
    
    home = df[df["IS_HOME"] == 1].copy()
    away = df[df["IS_HOME"] == 0].copy()

    roll_cols = [c for c in df.columns if c.startswith("ROLL10_")]
    keep_cols = ["GAME_ID", "TEAM_ID", "TEAM_NAME", "WIN", "SEASON"] + roll_cols

    home = home[keep_cols].rename(columns={
        **{c: f"AWAY_{c}" for c in roll_cols}, 
        "TEAM_ID": "AWAY_TEAM_ID",
        "TEAM_NAME": "AWAY_TEAM_NAME",
        "WIN": "AWAY_WIN",
    })

    matchups = home.merge(away, on = ["GAME_ID", "SEASON"], how = "inner")

    for col in roll_cols:
        home_col = f"HOME_{col}"
        away_col = f"AWAY_{col}"
        if home_col in matchups.columns and away_col in matchups.columns:
            matchups[f"DIFF_{col}"] = matchups[home_col] - matchups[away_col]

    return matchups.dropna()








    

