from pathlib import Path
from typing import Protocol

from models import FollowResult
from models import User


class GraphBuilder(Protocol):
    def add_user(self, user: User) -> None:
        ...

    def add_follow(self, from_id: int, to_id: int, record_history: bool = False) -> FollowResult:
        ...

    def add_block(self, blocker_id: int, blocked_id: int) -> bool:
        ...


def load_graph_from_folder(graph: GraphBuilder, folder_path: str | Path) -> None:
    folder = Path(folder_path)
    load_users(graph, folder / "users.txt")
    load_connections(graph, folder / "connections.txt")
    load_blocked(graph, folder / "blocked.txt")


def load_users(graph: GraphBuilder, file_path: str | Path) -> None:
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
            graph.add_user(User(user_id=user_id, username=username, bio=bio))


def load_connections(graph: GraphBuilder, file_path: str | Path) -> None:
    with Path(file_path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            from_id, to_id = parse_id_pair(line, line_number, "follow veze")
            graph.add_follow(from_id, to_id)


def load_blocked(graph: GraphBuilder, file_path: str | Path) -> None:
    path = Path(file_path)
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            blocker_id, blocked_id = parse_id_pair(line, line_number, "blokiranja")
            graph.add_block(blocker_id, blocked_id)


def parse_id_pair(line: str, line_number: int, label: str) -> tuple[int, int]:
    parts = line.split("|")
    if len(parts) != 2:
        raise ValueError(f"Neispravan format {label} u liniji {line_number}: {line}")
    return int(parts[0]), int(parts[1])
