import unittest

from src.personalization import apply_interest_profiles, selected_profile_names


class PersonalizationTest(unittest.TestCase):
    def test_apply_interest_profiles_merges_lists_without_duplicates(self):
        interests = {
            "preferred_topics": ["agent", "automation"],
            "preferred_languages": ["Python"],
        }
        profiles = {
            "java": {
                "preferred_topics": ["agent", "spring"],
                "preferred_languages": ["Java"],
            },
            "agent_development": {
                "preferred_topics": ["workflow"],
                "preferred_languages": ["TypeScript"],
            },
        }

        result = apply_interest_profiles(interests, profiles, ["java", "agent_development"])

        self.assertEqual(result["preferred_topics"], ["agent", "automation", "spring", "workflow"])
        self.assertEqual(result["preferred_languages"], ["Python", "Java", "TypeScript"])
        self.assertEqual(result["active_profiles"], ["java", "agent_development"])
        self.assertEqual(
            result["profile_match_rules"],
            [
                {
                    "name": "java",
                    "label": "java",
                    "preferred_topics": ["agent", "spring"],
                    "preferred_languages": ["Java"],
                },
                {
                    "name": "agent_development",
                    "label": "agent_development",
                    "preferred_topics": ["workflow"],
                    "preferred_languages": ["TypeScript"],
                },
            ],
        )

    def test_apply_interest_profiles_merges_score_weights(self):
        interests = {"score_weights": {"trending": 0.45, "topic": 0.15}}
        profiles = {
            "python": {
                "score_weights": {
                    "topic": 0.3,
                    "star_growth": 0.2,
                }
            }
        }

        result = apply_interest_profiles(interests, profiles, ["python"])

        self.assertEqual(
            result["score_weights"],
            {"trending": 0.45, "topic": 0.3, "star_growth": 0.2},
        )

    def test_apply_interest_profiles_records_missing_profile_error(self):
        result = apply_interest_profiles({}, {}, ["missing"])

        self.assertEqual(result["profile_errors"], ["未找到个性化 profile：missing"])
        self.assertNotIn("active_profiles", result)

    def test_selected_profile_names_supports_env_and_config(self):
        interests = {"active_profiles": ["java", "agent_development"]}

        self.assertEqual(selected_profile_names(interests, ""), ["java", "agent_development"])
        self.assertEqual(selected_profile_names(interests, "python, agent_development"), ["python", "agent_development"])
        self.assertEqual(selected_profile_names({"active_profile": "java;python"}, ""), ["java", "python"])


if __name__ == "__main__":
    unittest.main()
