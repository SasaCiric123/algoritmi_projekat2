from pathlib import Path
import sys

from models import FollowInteraction, User
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
    print(f"PageRank izracunat u {iterations} iteracija.")

    run_menu(graph)


def run_menu(graph: SocialGraph) -> None:
    while True:
        print("\n--- Meni ---")
        print("1. Pretraga korisnika")
        print("2. Prikaz najuticajnijih korisnika")
        print("3. Dodavanje nove follow veze")
        print("4. Prikaz istorije interakcija")
        print("5. BFS obilazak mreze")
        print("6. Autocomplete username")
        print("7. Preporuka korisnika")
        print("8. Izlaz")

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
            bfs_menu(graph)
        elif choice == "6":
            autocomplete_menu(graph)
        elif choice == "7":
            recommendations_menu(graph)
        elif choice == "8":
            print("Kraj programa.")
            break
        else:
            print("Nepostojeca opcija. Pokusajte ponovo.")


def search_users_menu(graph: SocialGraph) -> None:
    query = input("Unesite username ili rec iz biografije: ").strip()
    limit = 10
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
    limit = 10
    print("\nNajuticajniji korisnici:")
    for user, rank in graph.top_page_rank(limit=limit):
        print(f"- {format_user(user)} | PageRank={rank:.8f}")


def add_follow_menu(graph: SocialGraph) -> None:
    follower = read_user(graph, "Korisnik koji prati (id ili username): ")
    if follower is None:
        print("Nije moguce dodati vezu jer korisnik ne postoji.")
        return

    followed = read_user(graph, "Korisnik koji se prati (id ili username): ")
    if followed is None:
        print("Nije moguce dodati vezu jer korisnik ne postoji.")
        return

    result = graph.add_follow(follower.user_id, followed.user_id, record_history=True)
    if not result.success:
        print(result.message)
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


def bfs_menu(graph: SocialGraph) -> None:
    user = read_user(graph, "Unesite pocetnog korisnika (id ili username): ")
    if user is None:
        print("Korisnik ne postoji.")
        return

    max_level = read_positive_int("Do kog nivoa zelite obilazak: ", default=3)
    levels = graph.bfs_connections_by_level(user.user_id, max_level)

    if not levels:
        print("Nema dostiznih korisnika za zadati nivo.")
        return

    print(f"\nBFS konekcije za {format_user(user)}:")
    for level in range(1, max_level + 1):
        users = levels.get(level, [])
        print(f"Nivo {level}:")
        if not users:
            print("- nema korisnika")
            continue

        for connected_user in sorted(users, key=lambda item: item.username.lower()):
            print(f"- {format_user(connected_user)}")


def autocomplete_menu(graph: SocialGraph) -> None:
    prefix = input("Unesite pocetak username-a: ").strip()
    suggestions = graph.autocomplete_usernames(prefix, limit=10)

    if not suggestions:
        username_suggestions = graph.suggest_usernames(prefix, limit=5, max_distance=2)
        if username_suggestions:
            print("Nema tacnih autocomplete predloga. Da li ste mislili:")
            for user in username_suggestions:
                print(f"- {format_user(user)}")
            return

        print("Nema autocomplete predloga za zadati prefiks.")
        return

    print("\nAutocomplete predlozi:")
    for user in suggestions:
        rank = graph.page_rank.get(user.user_id, 0.0)
        print(f"- {format_user(user)} | PageRank={rank:.8f}")


def recommendations_menu(graph: SocialGraph) -> None:
    user = read_user(graph, "Unesite korisnika za preporuke (id ili username): ")
    if user is None:
        print("Korisnik ne postoji.")
        return

    alpha = read_alpha(default=0.5)
    recommendations = graph.recommend_users(user.user_id, alpha=alpha, limit=10)

    if not recommendations:
        print("Nema dostupnih preporuka za zadatog korisnika.")
        return

    print(f"\nPreporuke za {format_user(user)}:")
    for result in recommendations:
        print(
            f"- {format_user(result.user)} | score={result.score:.8f} "
            f"| PPR={result.ppr_score:.8f} | bio={result.content_similarity:.4f}"
        )


def read_user(graph: SocialGraph, prompt: str) -> User | None:
    value = input(prompt).strip()
    user = graph.get_user_by_id_or_username(value)
    if user is not None:
        return user

    if value and not value.isdigit():
        suggestions = graph.suggest_usernames(value, limit=5)
        if suggestions:
            print("Da li ste mislili:")
            for suggestion in suggestions:
                print(f"- {format_user(suggestion)}")

    return None


def read_limit(default: int = 10) -> int:
    return read_positive_int(f"Broj rezultata [{default}]: ", default)


def read_positive_int(prompt: str, default: int) -> int:
    value = input(prompt).strip()
    if not value:
        return default

    try:
        number = int(value)
    except ValueError:
        print(f"Neispravan broj. Koristim podrazumevano: {default}.")
        return default

    if number <= 0:
        print(f"Broj mora biti pozitivan. Koristim podrazumevano: {default}.")
        return default
    return number


def read_alpha(default: float = 0.5) -> float:
    value = input(f"Alpha, 0-1 [{default}]: ").strip()
    if not value:
        return default

    try:
        alpha = float(value)
    except ValueError:
        print(f"Neispravna alpha vrednost. Koristim podrazumevano: {default}.")
        return default

    if alpha < 0.0 or alpha > 1.0:
        print(f"Alpha mora biti izmedju 0 i 1. Koristim podrazumevano: {default}.")
        return default
    return alpha


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
