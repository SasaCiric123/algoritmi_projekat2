from pathlib import Path
import sys

from social_graph import SocialGraph


DEFAULT_DATASET = Path("data") / "dataset" / "dataset" / "small"


def main() -> None:
    dataset_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    graph = SocialGraph.load_from_folder(dataset_path)

    print("Drustvena mreza je uspesno ucitana.")
    print(f"Dataset: {dataset_path}")
    print(f"Broj korisnika: {len(graph.users_by_id)}")
    print(f"Broj follow veza: {graph.connection_count}")
    print(f"Broj blokiranja: {graph.blocked_count}")

    iterations = graph.calculate_page_rank()
    print(f"\nPageRank izracunat u {iterations} iteracija.")
    print("Najuticajniji korisnici po PageRank-u:")
    for user, rank in graph.top_page_rank(limit=5):
        print(f"- {user.username} (id={user.user_id}) - PageRank: {rank:.8f}")

    most_followed = graph.most_followed(limit=5)
    print("\nKorisnici sa najvise pratilaca:")
    for user, follower_count in most_followed:
        print(f"- {user.username} (id={user.user_id}) - pratioci: {follower_count}")

    print("\nPrimer pretrage za upit 'vegan':")
    for result in graph.search_users("vegan", limit=5):
        print(
            f"- {result.user.username} (id={result.user.user_id}) "
            f"- relevance: {result.relevance:.1f}, PageRank: {result.page_rank:.8f}"
        )


if __name__ == "__main__":
    main()
