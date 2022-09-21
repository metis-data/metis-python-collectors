from unittest import TestCase

from common.utils.chunk import chunk_string_list


class TestChunker(TestCase):
    def test_chunk_string_list(self):
        string_lengths = (1, 3, 9, 3, 5, 8, 22, 9, 72, 4)
        strings = ['x'*i for i in string_lengths]
        for i in range(1, sum(len(s) for s in strings) + 1):
            prev_len = None
            for chunk in chunk_string_list(strings, i):
                chunk = list(chunk)
                chunk_len = sum(len(s) for s in chunk)
                self.assertTrue(chunk)
                if len(chunk[0]) > i:
                    self.assertEqual(len(chunk), 1)
                else:
                    self.assertLessEqual(chunk_len, i)
                if prev_len is not None:
                    self.assertGreater(prev_len + chunk_len, i)
                prev_len = chunk_len

    def test_chunk_string_list_empty_list(self):
        self.assertFalse(list(chunk_string_list([], 5)))
