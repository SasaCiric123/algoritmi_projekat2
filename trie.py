from dataclasses import dataclass, field


@dataclass
class TrieNode: #jedan cvor u stablu
    children: dict[str, "TrieNode"] = field(default_factory=dict) #cuva slova
    user_ids: list[int] = field(default_factory=list) #cuva id korisnika cije se ime zavrsava u ovom cvoru


class Trie: #stablo slicno onom iz proslog projekta
    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, word: str, user_id: int) -> None: #ide slovo po slovo i ubacuje u stablo
        node = self.root
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.user_ids.append(user_id)

    def search_prefix(self, prefix: str) -> list[int]:
        node = self.root
        for char in prefix.lower():
            if char not in node.children: #ide slovo po slovo npr s a l e, ako negde nema da ode, znaci da ne postoji username sa ovim prefixom
                return []
            node = node.children[char]

        user_ids: list[int] = [] #ovde sam presao sva slova, uzimaju se id od korisnika koji su u tom cvoru i vracaju se
        self._collect_user_ids(node, user_ids)
        return user_ids

    def _collect_user_ids(self, node: TrieNode, user_ids: list[int]) -> None:
        user_ids.extend(node.user_ids)
        for child in node.children.values():
            self._collect_user_ids(child, user_ids)
