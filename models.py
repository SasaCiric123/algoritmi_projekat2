from dataclasses import dataclass


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


@dataclass(frozen=True)
class FollowInteraction:
    order: int
    from_id: int
    to_id: int


@dataclass(frozen=True)
class FollowResult:
    success: bool
    message: str
