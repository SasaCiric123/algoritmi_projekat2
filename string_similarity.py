def levenshtein_distance(first: str, second: str) -> int:
    first = first.lower()
    second = second.lower()

    if first == second:
        return 0
    if not first:
        return len(second)
    if not second:
        return len(first)

    previous_row = list(range(len(second) + 1))

    for i, first_char in enumerate(first, start=1):
        current_row = [i]
        for j, second_char in enumerate(second, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            replace_cost = previous_row[j - 1] + (first_char != second_char)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row

    return previous_row[-1]
