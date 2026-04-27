import unittest

from src.utils import chunk_text


class UtilsTest(unittest.TestCase):
    def test_chunk_text_keeps_limit(self):
        text = "\n\n".join([f"## Section {index}\n" + "x" * 100 for index in range(20)])
        chunks = chunk_text(text, limit=350)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 350 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()

