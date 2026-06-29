from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import heapq
from pathlib import Path
import re


@dataclass(frozen=True)
class User:
    user_id: int
    username: str
    bio: str


@dataclass(frozen=True)
class SearchResult:
    user: User
    relevance: float
    page_rank: float
    score: float


class SocialGraph:
    def __init__(self) -> None:
        self.users_by_id: dict[int, User] = {}
        self.user_id_by_username: dict[str, int] = {}
        self.inverted_index: dict[str, set[int]] = defaultdict(set)#rec -> skup korisnika kod kojih se ta rec pojavljuje u bio
        self.bio_words_by_user: dict[int, set[str]] = {}

        self.following: dict[int, set[int]] = defaultdict(set)
        self.followers: dict[int, set[int]] = defaultdict(set)
        self.out_degree: dict[int, int] = defaultdict(int)

        self.blocked_by_user: dict[int, set[int]] = defaultdict(set)
        self.blocked_count = 0
        self.connection_count = 0
        self.page_rank: dict[int, float] = {}

    @classmethod
    def load_from_folder(cls, folder_path: str | Path) -> SocialGraph:
        folder = Path(folder_path)
        graph = cls()

        graph.load_users(folder / "users.txt")
        graph.load_connections(folder / "connections.txt")
        graph.load_blocked(folder / "blocked.txt")

        return graph

    def load_users(self, file_path: str | Path) -> None:
        with Path(file_path).open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split("|", maxsplit=2)
                if len(parts) != 3:
                    raise ValueError(f"Neispravan format korisnika u liniji {line_number}: {line}")

                user_id = int(parts[0])
                username = parts[1]
                bio = parts[2]
                self.add_user(User(user_id=user_id, username=username, bio=bio))

    def load_connections(self, file_path: str | Path) -> None:
        with Path(file_path).open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                if not line:
                    continue

                from_id, to_id = self._parse_id_pair(line, line_number, "follow veze")
                self.add_follow(from_id, to_id)

    def load_blocked(self, file_path: str | Path) -> None:
        path = Path(file_path)
        if not path.exists():
            return

        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                if not line:
                    continue

                blocker_id, blocked_id = self._parse_id_pair(line, line_number, "blokiranja")
                self.add_block(blocker_id, blocked_id)

    def add_user(self, user: User) -> None:
        if user.user_id in self.users_by_id:
            raise ValueError(f"Korisnik sa id={user.user_id} vec postoji.")

        username_key = user.username.lower()
        if username_key in self.user_id_by_username:
            raise ValueError(f"Korisnicko ime '{user.username}' vec postoji.")

        self.users_by_id[user.user_id] = user
        self.user_id_by_username[username_key] = user.user_id
        self.page_rank[user.user_id] = 0.0

        bio_words = set(self._tokenize_text(user.bio))
        self.bio_words_by_user[user.user_id] = bio_words
        for word in bio_words:
            self.inverted_index[word].add(user.user_id)

    def add_follow(self, from_id: int, to_id: int) -> bool:
        self._ensure_known_user(from_id)
        self._ensure_known_user(to_id)

        if to_id in self.following[from_id]:
            return False

        self.following[from_id].add(to_id)
        self.followers[to_id].add(from_id)
        self.out_degree[from_id] += 1
        self.connection_count += 1
        return True

    def add_block(self, blocker_id: int, blocked_id: int) -> bool:
        self._ensure_known_user(blocker_id)
        self._ensure_known_user(blocked_id)

        if blocked_id in self.blocked_by_user[blocker_id]:
            return False

        self.blocked_by_user[blocker_id].add(blocked_id)
        self.blocked_count += 1
        return True

    def get_user_by_username(self, username: str) -> User | None:
        user_id = self.user_id_by_username.get(username.lower())
        if user_id is None:
            return None
        return self.users_by_id[user_id]

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

        relevance_by_user: dict[int, float] = defaultdict(float)
        query_words = set(self._tokenize_text(query))

        for username_key, user_id in self.user_id_by_username.items():
            if username_key == query:
                relevance_by_user[user_id] += 3.0
            elif username_key.startswith(query):
                relevance_by_user[user_id] += 2.0
            elif query in username_key:
                relevance_by_user[user_id] += 1.0

        for word in query_words:
            for user_id in self.inverted_index.get(word, set()):
                relevance_by_user[user_id] += 1.0

        results = []
        for user_id, relevance in relevance_by_user.items():
            page_rank = self.page_rank.get(user_id, 0.0)
            score = relevance + page_rank
            results.append(
                SearchResult(
                    user=self.users_by_id[user_id],
                    relevance=relevance,
                    page_rank=page_rank,
                    score=score,
                )
            )

        return heapq.nlargest(
            limit,
            results,
            key=lambda result: (result.score, result.page_rank, result.user.username.lower()),
        )

    def _ensure_known_user(self, user_id: int) -> None:
        if user_id not in self.users_by_id:
            raise ValueError(f"Nepoznat korisnik id={user_id}.")

    @staticmethod
    def _parse_id_pair(line: str, line_number: int, label: str) -> tuple[int, int]:
        parts = line.split("|")
        if len(parts) != 2:
            raise ValueError(f"Neispravan format {label} u liniji {line_number}: {line}")
        return int(parts[0]), int(parts[1])

    @staticmethod
    def _tokenize_text(text: str) -> list[str]:#prebacuje u mala slova, izdvaja reci
        return re.findall(r"[a-z0-9_]+", text.lower())
