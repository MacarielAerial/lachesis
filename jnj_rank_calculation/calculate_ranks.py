import itertools
import numpy as np
import pandas as pd

def calculate_relative_placement(scores):
    num_competitors, num_judges = scores.shape
    # Initialize results
    final_rankings = np.zeros(num_competitors, dtype=int)
    majority_threshold = num_judges // 2 + 1
    
    def get_ordinal_sums(indices, rank):
        return [np.sum(scores[i, scores[i] <= rank]) for i in indices]
    
    n_pass = 1
    while len(np.unique(final_rankings)) != len(final_rankings):
        print(f"Start pass {n_pass}")
        # Simple Majority check
        for i in range(len(final_rankings)):
            if final_rankings[i] == 0:
                for current_rank in range(1, len(final_rankings) + 1):
                    majority_count = np.count_nonzero(scores[i] <= current_rank)
                    if majority_count >= majority_threshold:
                        print(f"Assigning rank {current_rank} to ordinally indexed competitor {i}")
                        final_rankings[i] = current_rank
                        break

        # Identify all available ranks to find all possible ties
        all_ranks = np.unique(final_rankings)

        # Resolve ties
        for current_rank in all_ranks:
            tied_all = np.where(final_rankings == current_rank)[0]
            if len(tied_all) > 1:
                choosed_2_tied = np.array(list(itertools.combinations(tied_all, r=2)))
                for tied in choosed_2_tied:
                    print(f"Attempting to resolve rank {current_rank} tie between competitor ordinallly indexed {tied}")
                    # Tie break - cumulative majority before ordinal sum
                    for cu_majority_rank in range(1, num_competitors + 1):
                        majority_counts = []
                        for tie_index in tied:
                            majority_count = np.count_nonzero(scores[tie_index] <= cu_majority_rank)
                            majority_counts.append(majority_count)
                        
                        # Calculate if the current majority rank results in majorities in either tied competitor
                        either_over_thold = any([count >= majority_threshold for count in majority_counts])
                        if not either_over_thold:
                            # None has majority
                            continue
                        
                        # Different majorities - cumulative majority rule
                        print(tied, cu_majority_rank, majority_counts)
                        if len(set(majority_counts)) == len(majority_counts):
                            order = np.argsort(majority_counts)[::-1]
                            for idx, tie_index in enumerate(tied[order]):
                                final_rankings[tie_index] = current_rank + idx
                                print(current_rank)
                                print("Cumulative majority", tie_index, final_rankings[tie_index])
                            # Cumulative majority rule fired. No need for ordinal sum
                            break
                        # Same majority - ordinal sum rule
                        else:
                            print(f"Failed to break tie with cumulative majority rule for tie {tied}. Switching to ordinal sum rule")
                            ordinal_sums = get_ordinal_sums(tied, current_rank)
                            print(f"Ordinal sums for {tied}: {ordinal_sums}")
                            if len(set(ordinal_sums)) == len(ordinal_sums):  # If ordinal sums are unique
                                order = np.argsort(ordinal_sums)
                                for idx, tie_index in enumerate(tied[order]):
                                    # Lower ordinal sum leads to lower rank
                                    final_rankings[tie_index] = current_rank + idx
                                    print("Ordinal Sum", tie_index, final_rankings[tie_index])
                                break
                            else:  # Increment ranks based on next placement's ordinal sums
                                assert False
                                for next_rank in range(current_rank + 1, num_competitors + 1):
                                    ordinal_sums = get_ordinal_sums(tied, next_rank)
                                    if len(set(ordinal_sums)) == len(ordinal_sums):  # Break tie with unique ordinal sums
                                        order = np.argsort(ordinal_sums)
                                        for idx, tie_index in enumerate(tied[order]):
                                            final_rankings[tie_index] = current_rank + idx
                                        break
                        
        n_pass += 1
        print(final_rankings)
        if n_pass == 7:
            assert False
    
    # Reassign final rankings to be relative rankings to ensure they start from 1 and are sequential
    unique_ranks = np.sort(final_rankings)
    # Replace ordinal-sum adjusted majority-based ranks with their indices after sorting
    for new_rank, original_rank in enumerate(unique_ranks, start=1):
        final_rankings[final_rankings == original_rank] = new_rank

    return final_rankings


if __name__ == "__main__":
    df = pd.read_csv("./jnj_cologne_2025_intermediate.csv")
    df["Bib#"] = df["Bib#"].astype(int)
    df["Rank"] = df["Rank"].astype(int)
    df["J1"] = df["J1"].astype(int)
    df["J2"] = df["J2"].astype(int)
    df["J3"] = df["J3"].astype(int)
    df["J4"] = df["J4"].astype(int)
    df["J5"] = df["J5"].astype(int)

    scores = df[["J1", "J2", "J3", "J4", "J5"]].values

    final_rankings = calculate_relative_placement(scores)

    bibs = df["Bib#"].values.tolist()

    bib_to_rank = dict(zip(bibs, final_rankings))

    print(bib_to_rank)
