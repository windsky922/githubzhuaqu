import unittest

from src.collector import _readme_excerpt


class CollectorTest(unittest.TestCase):
    def test_readme_excerpt_normalizes_whitespace_and_limits_length(self):
        readme = "# Title\n\n" + "word " * 20

        result = _readme_excerpt(readme, limit=18)

        self.assertEqual(result, "# Title word word ")
        self.assertLessEqual(len(result), 18)


if __name__ == "__main__":
    unittest.main()
