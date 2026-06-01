import time
import pandas as pd
from nba_api.stats.endpoints import TeamGameLog, BoxScoreAdvancedV2
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

    return pd.concat(all_rows, ignore_index=True)

def _clean_team_log(df):
    """
    Extracts Home/Away data. Classifies with WIN/LOSE label.
    """
    df["WIN"] = (df["WIN"] == "W").astype(int)
    df["IS_HOME"] = df["MATCHUP"].apply(
        lambda x: 1 if "vs." in x else 0
    )
    df["OPP_ABB"] = df["MATCHUP"].apply(
        lambda x: x.split("vs.  ")[-1] if "vs. " in x else x.split("@ ")[-1]
    )
    return df



    

