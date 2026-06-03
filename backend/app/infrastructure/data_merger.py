import pandas as pd
from app.infrastructure.text_utils import normalize_text as _normalize


class PlayerDataMerger:
    """Joins FBref penalty data onto a Sofascore DataFrame, matching players by normalised name and team."""

    def merge(self, sofascore_df: pd.DataFrame, fbref_df: pd.DataFrame) -> pd.DataFrame:
        """Join FBref pk_won onto the Sofascore DataFrame by normalized name+team."""
        ss = sofascore_df.copy()
        fb = fbref_df.copy()

        ss["_norm_name"] = ss["name"].map(_normalize)
        ss["_norm_team"] = ss["team"].map(_normalize)
        fb["_norm_name"] = fb["player_name"].map(_normalize)
        fb["_norm_team"] = fb["team"].map(_normalize)

        fb_indexed = fb.set_index(["_norm_name", "_norm_team"])["pk_won"]

        def lookup_pk_won(row: pd.Series) -> int:
            return int(fb_indexed.get((row["_norm_name"], row["_norm_team"]), 0))

        ss["pk_won"] = ss.apply(lookup_pk_won, axis=1)
        ss.drop(columns=["_norm_name", "_norm_team"], inplace=True)
        return ss
