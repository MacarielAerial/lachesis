import itertools
from pathlib import Path
from typing import Tuple
from pandas import DataFrame
import numpy as np
import pandas as pd
import logging
import io


logger = logging.getLogger(__name__)


def load_df_scores_from_csv(path_csv: Path) -> DataFrame:
    df = pd.read_csv(path_csv)

    df["Bib#"] = df["Bib#"].astype(int)
    df["Rank"] = df["Rank"].astype(int)
    df["J1"] = df["J1"].astype(int)
    df["J2"] = df["J2"].astype(int)
    df["J3"] = df["J3"].astype(int)
    df["J4"] = df["J4"].astype(int)
    df["J5"] = df["J5"].astype(int)

    logger.info(f"Parsed a scores dataframe shaped {df.shape}")

    # Shuffle the input so that the original ranking info isn't available
    df = df.sample(frac=1).reset_index()

    logger.info(f"Loaded a shuffled score Dataframe:\n{df}")

    return df

def calculate_relative_placement(df_scores: pd.DataFrame) -> (pd.DataFrame, str):
    scores = df_scores[["J1", "J2", "J3", "J4", "J5"]].values
    num_competitors, num_judges = scores.shape
    threshold = num_judges // 2 + 1

    # Prepare log capture
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

    logger.info(f"Total judges: {num_judges}, majority threshold: {threshold}\n")

    final = np.zeros(num_competitors, dtype=int)
    pass_num = 1
    def ordinal_sums(idxs, r):
        return [int(np.sum(scores[i, scores[i] <= r])) for i in idxs]

    # Repeat until all unique
    while len(np.unique(final)) != len(final):
        logger.info(f"--- Pass {pass_num} ---")
        # Simple-majority assignment
        for i in range(num_competitors):
            if final[i] != 0:
                continue
            for k in range(1, num_competitors + 1):
                cnt = int(np.count_nonzero(scores[i] <= k))
                if cnt >= threshold:
                    bib = int(df_scores.at[i, 'Bib#'])
                    logger.info(f"Bib {bib}: {cnt} judges ≤ {k} → provisional {k}")
                    final[i] = k
                    break

        # Tie-breaking
        for place in sorted(np.unique(final)):
            tied = np.where(final == place)[0]
            if len(tied) <= 1:
                continue
            bibs_tied = df_scores.loc[tied, 'Bib#'].tolist()
            logger.info(f"Tie at provisional place {place} among Bibs {bibs_tied}")
            # Check all pairs for resolution
            for a, b in itertools.combinations(tied, 2):
                for r in range(1, num_competitors + 1):
                    counts = [int(np.count_nonzero(scores[j] <= r)) for j in (a, b)]
                    if max(counts) < threshold:
                        continue
                    if counts[0] != counts[1]:
                        # cumulative majority
                        winner, loser = (a, b) if counts[0] > counts[1] else (b, a)
                        bib_w = int(df_scores.at[winner, 'Bib#'])
                        bib_l = int(df_scores.at[loser, 'Bib#'])
                        final[winner] = place
                        final[loser] = place + 1
                        logger.info(f"Cumulative-majority at r={r}: counts {counts} → Bib {bib_w} ahead of Bib {bib_l}")
                        break
                    else:
                        # ordinal-sum
                        sums = ordinal_sums((a, b), place)
                        if sums[0] != sums[1]:
                            winner, loser = (a, b) if sums[0] < sums[1] else (b, a)
                            bib_w = int(df_scores.at[winner, 'Bib#'])
                            bib_l = int(df_scores.at[loser, 'Bib#'])
                            final[winner] = place
                            final[loser] = place + 1
                            logger.info(f"Ordinal-sum at place={place}: sums {sums} → Bib {bib_w} ahead of Bib {bib_l}")
                            break
                # end for r

        provisional = dict(zip(df_scores['Bib#'].tolist(), final.tolist()))
        logger.info(f"Provisional ranks after pass {pass_num}: {provisional}\n")
        pass_num += 1

    # Normalize to 1…n
    uniq = np.unique(final)
    for new, old in enumerate(sorted(uniq), start=1):
        final[final == old] = new

    # Build output DataFrame
    df_out = pd.DataFrame({
        'Bib#': df_scores['Bib#'],
        'Leader': df_scores['Leader'],
        'Follower': df_scores['Follower'],
        'Placement': final
    })
    df_out = df_out.sort_values('Placement').reset_index(drop=True)

    # Extract logs
    logger.removeHandler(handler)
    log_text = log_stream.getvalue()
    log_stream.close()

    return df_out, log_text
