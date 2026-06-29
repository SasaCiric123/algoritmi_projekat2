from pathlib import Path
import sys

from social_graph import FollowInteraction, SocialGraph, User


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
    print(f"PageRank izracunat u {iterations} iteracija.")

    run_menu(graph)


def run_menu(graph: SocialGraph) -> None:
    while True:
        print("\n--- Meni ---")
        print("1. Pretraga korisnika")
        print("2. Prikaz najuticajnijih korisnika")
        print("3. Dodavanje nove follow veze")
        print("4. Prikaz istorije interakcija")
        print("5. Izlaz")

        choice = input("Izaberite opciju: ").strip()

        if choice == "1":
            search_users_menu(graph)
        elif choice == "2":
            show_top_page_rank_menu(graph)
        elif choice == "3":
            add_follow_menu(graph)
        elif choice == "4":
            show_history_menu(graph)
        elif choice == "5":
            print("Kraj programa.")
            break
        else:
            print("Nepostojeca opcija. Pokusajte ponovo.")


def search_users_menu(graph: SocialGraph) -> None:
    query = input("Unesite username ili rec iz biografije: ").strip()
    limit = read_limit()
    results = graph.search_users(query, limit=limit)

    if not results:
        print("Nema rezultata za zadati upit.")
        return

    print("\nRezultati pretrage:")
    for result in results:
        print(
            f"- {format_user(result.user)} | relevance={result.relevance:.1f} "
            f"| PageRank={result.page_rank:.8f} | score={result.score:.8f}"
        )


def show_top_page_rank_menu(graph: SocialGraph) -> None:
    limit = read_limit()
    print("\nNajuticajniji korisnici:")
    for user, rank in graph.top_page_rank(limit=limit):
        print(f"- {format_user(user)} | PageRank={rank:.8f}")


def add_follow_menu(graph: SocialGraph) -> None:
    follower = read_user(graph, "Korisnik koji prati (id ili username): ")
    followed = read_user(graph, "Korisnik koji se prati (id ili username): ")

    if follower is None or followed is None:
        print("Nije moguce dodati vezu jer korisnik ne postoji.")
        return

    added = graph.add_follow(follower.user_id, followed.user_id, record_history=True)
    if not added:
        print("Veza nije dodata. Korisnik mozda vec prati zadatog korisnika ili je izabran isti korisnik.")
        return

    iterations = graph.calculate_page_rank()
    print(f"Dodata je veza: {follower.username} -> {followed.username}")
    print(f"PageRank je ponovo izracunat u {iterations} iteracija.")


def show_history_menu(graph: SocialGraph) -> None:
    user = read_user(graph, "Unesite korisnika za prikaz istorije (id ili username): ")
    if user is None:
        print("Korisnik ne postoji.")
        return

    history = graph.get_interaction_history(user.user_id)
    if not history:
        print("Nema novih interakcija za ovog korisnika tokom trenutnog pokretanja programa.")
        return

    print(f"\nIstorija interakcija za {format_user(user)}:")
    for interaction in history:
        print(format_interaction(graph, user, interaction))


def read_user(graph: SocialGraph, prompt: str) -> User | None:
    value = input(prompt).strip()
    return graph.get_user_by_id_or_username(value)


def read_limit(default: int = 10) -> int:
    value = input(f"Broj rezultata [{default}]: ").strip()
    if not value:
        return default

    try:
        limit = int(value)
    except ValueError:
        print(f"Neispravan broj. Koristim podrazumevano: {default}.")
        return default

    if limit <= 0:
        print(f"Broj mora biti pozitivan. Koristim podrazumevano: {default}.")
        return default
    return limit


def format_interaction(graph: SocialGraph, selected_user: User, interaction: FollowInteraction) -> str:
    follower = graph.users_by_id[interaction.from_id]
    followed = graph.users_by_id[interaction.to_id]

    if selected_user.user_id == interaction.from_id:
        return f"{interaction.order}. Zapratio je korisnika {format_user(followed)}"
    return f"{interaction.order}. Zapratio ga je korisnik {format_user(follower)}"


def format_user(user: User) -> str:
    return f"{user.username} (id={user.user_id})"


if __name__ == "__main__":
    main()
