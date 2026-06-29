from dataclasses import dataclass, field


@dataclass
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    user_ids: list[int] = field(default_factory=list)


class Trie:
    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, word: str, user_id: int) -> None:
        node = self.root
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.user_ids.append(user_id)

    def search_prefix(self, prefix: str) -> list[int]:
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]

        user_ids: list[int] = []
        self._collect_user_ids(node, user_ids)
        return user_ids

    def _collect_user_ids(self, node: TrieNode, user_ids: list[int]) -> None:
        user_ids.extend(node.user_ids)
        for child in node.children.values():
            self._collect_user_ids(child, user_ids)
