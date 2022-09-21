from typing import List


def chunk_string_list(str_list: List[str], max_len: int):
    if not str_list:
        return

    def _next_chunk():
        nonlocal start
        total = 0
        while start < list_len:
            curr_len = len(str_list[start])
            if total != 0 and total + curr_len > max_len:
                break
            yield str_list[start]
            start += 1
            total += curr_len

    start = 0
    list_len = len(str_list)
    while start < list_len:
        yield _next_chunk()
