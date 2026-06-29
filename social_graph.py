from __future__ import annotations

from collections import defaultdict, deque
import heapq
from pathlib import Path

from data_loader import load_graph_from_folder
from models import FollowInteraction, FollowResult, SearchResult, User
from string_similarity import levenshtein_distance
from text_processing import tokenize_text
from trie import Trie


class SocialGraph:
    def __init__(self) -> None:
        self.users_by_id: dict[int, User] = {}
        self.user_id_by_username: dict[str, int] = {}
        self.username_trie = Trie()
        self.inverted_index: dict[str, set[int]] = defaultdict(set)#rec -> skup korisnika kod kojih se ta rec pojavljuje u bio
        self.bio_words_by_user: dict[int, set[str]] = {}

        self.following: dict[int, set[int]] = defaultdict(set)
        self.followers: dict[int, set[int]] = defaultdict(set)
        self.out_degree: dict[int, int] = defaultdict(int)

        self.blocked_by_user: dict[int, set[int]] = defaultdict(set)
        self.blocked_count = 0
        self.connection_count = 0
        self.page_rank: dict[int, float] = {}
        self.following_history: dict[int, list[FollowInteraction]] = defaultdict(list)
        self.follower_history: dict[int, list[FollowInteraction]] = defaultdict(list)
        self._interaction_counter = 0

    @classmethod
    def load_from_folder(cls, folder_path: str | Path) -> SocialGraph:
        graph = cls()
        load_graph_from_folder(graph, folder_path)
        return graph

    def add_user(self, user: User) -> None:
        if user.user_id in self.users_by_id:
            raise ValueError(f"Korisnik sa id={user.user_id} vec postoji.")

        username_key = user.username.lower()
        if username_key in self.user_id_by_username:
            raise ValueError(f"Korisnicko ime '{user.username}' vec postoji.")

        self.users_by_id[user.user_id] = user
        self.user_id_by_username[username_key] = user.user_id
        self.username_trie.insert(user.username, user.user_id) #dodaje slova u stablo
        self.page_rank[user.user_id] = 0.0

        bio_words = set(tokenize_text(user.bio))
        self.bio_words_by_user[user.user_id] = bio_words
        for word in bio_words:
            self.inverted_index[word].add(user.user_id) #dodajem reci iz bio-a u inverted index

    def add_follow(self, from_id: int, to_id: int, record_history: bool = False) -> FollowResult:
        self._ensure_known_user(from_id)
        self._ensure_known_user(to_id)

        if from_id == to_id:
            return FollowResult(False, "Korisnik ne moze da prati samog sebe.")

        if self.is_blocked_between(from_id, to_id):
            return FollowResult(False, "Veza nije dozvoljena jer postoji blokiranje izmedju korisnika.")

        if to_id in self.following[from_id]:
            return FollowResult(False, "Korisnik vec prati zadatog korisnika.")

        self.following[from_id].add(to_id)
        self.followers[to_id].add(from_id)
        self.out_degree[from_id] += 1
        self.connection_count += 1

        if record_history:
            self._interaction_counter += 1
            interaction = FollowInteraction(
                order=self._interaction_counter,
                from_id=from_id,
                to_id=to_id,
            )
            self.following_history[from_id].append(interaction)
            self.follower_history[to_id].append(interaction)

        return FollowResult(True, "Veza je uspesno dodata.")

    def add_block(self, blocker_id: int, blocked_id: int) -> bool:
        self._ensure_known_user(blocker_id)
        self._ensure_known_user(blocked_id)

        if blocked_id in self.blocked_by_user[blocker_id]:
            return False

        self.blocked_by_user[blocker_id].add(blocked_id)
        self.blocked_count += 1
        return True

    def is_blocked_between(self, first_id: int, second_id: int) -> bool:
        return (
            second_id in self.blocked_by_user[first_id]
            or first_id in self.blocked_by_user[second_id]
        )

    def get_user_by_username(self, username: str) -> User | None:
        user_id = self.user_id_by_username.get(username.lower())
        if user_id is None:
            return None
        return self.users_by_id[user_id]

    def get_user_by_id_or_username(self, value: str) -> User | None:
        value = value.strip()
        if value.isdigit():
            return self.users_by_id.get(int(value))
        return self.get_user_by_username(value)

    def most_followed(self, limit: int = 10) -> list[tuple[User, int]]:
        ranked = sorted(
            self.users_by_id.values(),
            key=lambda user: len(self.followers[user.user_id]),
            reverse=True,
        )
        return [(user, len(self.followers[user.user_id])) for user in ranked[:limit]]

    def calculate_page_rank(
        self,
        damping_factor: float = 0.85,
        epsilon: float = 1e-6,
        max_iterations: int = 100,
    ) -> int:
        user_ids = list(self.users_by_id.keys())
        user_count = len(user_ids)
        if user_count == 0:
            self.page_rank = {}
            return 0

        initial_rank = 1.0 / user_count
        ranks = {
            user_id: self.page_rank.get(user_id, initial_rank) or initial_rank
            for user_id in user_ids
        }

        for iteration in range(1, max_iterations + 1):
            dangling_sum = sum( #ovo su korisnici koji ne prate nikog
                ranks[user_id]
                for user_id in user_ids
                if self.out_degree[user_id] == 0
            )
            dangling_share = dangling_sum / user_count #posto nikog ne prati njegova vrednost nema gde da ode
                                                        #zato mu dajemo vrednost u odnosu na koliko korisnika ima
            base_rank = (1.0 - damping_factor) / user_count #posto je ovaj faktor 0.85, 1-0,85 je 0.15, sto je 15 % sanse da korisnik ode na grafu negde nasumicno
            new_ranks = {}
            max_change = 0.0

            for user_id in user_ids: #prolazi kroz sve koji ga prate
                incoming_rank = 0.0
                for follower_id in self.followers[user_id]:
                    incoming_rank += ranks[follower_id] / self.out_degree[follower_id] #Ako korisnik A prati korisnika B, onda A daje deo svoje PageRank vrednosti korisniku B.
                                                                                        #Ali ako A prati 10 korisnika, onda se njegova vrednost deli na 10 delova.

                new_rank = base_rank + damping_factor * (incoming_rank + dangling_share)#base-svi imaju, damping-oni koji nikog ne prate, incoming_rank-od pratioca
                new_ranks[user_id] = new_rank
                max_change = max(max_change, abs(new_rank - ranks[user_id]))#pratim koliko se vrednost promenila

            ranks = new_ranks
            if max_change < epsilon:
                break

        self.page_rank = ranks
        return iteration

    def top_page_rank(self, limit: int = 10) -> list[tuple[User, float]]:
        top_items = heapq.nlargest(
            limit,
            self.page_rank.items(),
            key=lambda item: item[1],#ovo je page rank vrednost korisnika
        )
        return [(self.users_by_id[user_id], rank) for user_id, rank in top_items]

    def search_users(self, query: str, limit: int = 10) -> list[SearchResult]:
        query = query.strip().lower()
        if not query:
            return []

        relevance_by_user: dict[int, float] = defaultdict(float) #ovde skupljam bodove za svakog korisnika
        query_words = set(tokenize_text(query))

        for username_key, user_id in self.user_id_by_username.items():
            if username_key == query:
                relevance_by_user[user_id] += 3.0
            elif username_key.startswith(query):
                relevance_by_user[user_id] += 2.0
            elif query in username_key:
                relevance_by_user[user_id] += 1.0

        for word in query_words: #prolazi kroz sve reci iz bio-a tako sto pogleda inverted index
            for user_id in self.inverted_index.get(word, set()):
                relevance_by_user[user_id] += 1.0

        results = []
        for user_id, relevance in relevance_by_user.items():
            page_rank = self.page_rank.get(user_id, 0.0)
            score = relevance + page_rank #sto je uticanjniji korisnik, score je veci
            results.append(
                SearchResult(
                    user=self.users_by_id[user_id],
                    relevance=relevance,
                    page_rank=page_rank,
                    score=score,
                )
            )

        return heapq.nlargest( #uzima sve rezultate i sortira, te vraca koliki je limit
            limit,
            results,
            key=lambda result: (result.score, result.page_rank, result.user.username.lower()),
        )

    def autocomplete_usernames(self, prefix: str, limit: int = 10) -> list[User]:
        prefix = prefix.strip().lower()
        if not prefix:
            return []

        user_ids = self.username_trie.search_prefix(prefix) #prolazi kroz sve username-e i vraca id-e
        users = [self.users_by_id[user_id] for user_id in user_ids] #svi korisnici koji se poklapaju
        return heapq.nlargest( #vraca onoliko koliki je limit
            limit,
            users,
            key=lambda user: (self.page_rank.get(user.user_id, 0.0), user.username.lower()),
        )

    def suggest_usernames(self, username: str, limit: int = 5) -> list[User]:
        username = username.strip().lower()
        if not username:
            return []

        max_distance = max(2, len(username) // 2 + 1)
        candidates = []
        for user in self.users_by_id.values():
            distance = levenshtein_distance(username, user.username)
            if distance > max_distance:
                continue
            candidates.append((distance, -self.page_rank.get(user.user_id, 0.0), user.username.lower(), user))

        closest = heapq.nsmallest(limit, candidates, key=lambda item: item[:3])
        return [user for _, _, _, user in closest]

    def get_interaction_history(self, user_id: int) -> list[FollowInteraction]:
        self._ensure_known_user(user_id)
        interactions = self.following_history[user_id] + self.follower_history[user_id]
        return sorted(interactions, key=lambda interaction: interaction.order)

    def bfs_connections_by_level(self, start_id: int, max_level: int) -> dict[int, list[User]]:
        self._ensure_known_user(start_id)
        if max_level <= 0:
            return {}

        visited = {start_id}
        queue = deque([(start_id, 0)])
        levels: dict[int, list[User]] = defaultdict(list)

        while queue:
            current_id, current_level = queue.popleft()
            if current_level == max_level:
                continue

            next_level = current_level + 1
            for neighbor_id in self.following[current_id]:
                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)
                levels[next_level].append(self.users_by_id[neighbor_id])
                queue.append((neighbor_id, next_level))

        return dict(levels)

    def _ensure_known_user(self, user_id: int) -> None:
        if user_id not in self.users_by_id:
            raise ValueError(f"Nepoznat korisnik id={user_id}.")
