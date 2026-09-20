from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_experimental_release_first_use_contract_is_present(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        runbook = (ROOT / "docs" / "release" / "public-candidate.md").read_text(
            encoding="utf-8"
        )
        acceptance = (ROOT / "docs" / "adr" / "0006-experimental-oss-publication.md").read_text(
            encoding="utf-8"
        )
        combined = "\n".join((readme, runbook, acceptance))

        self.assertIn("No GitHub account or token", readme)
        self.assertIn("releases/tag/v0.2.0-experimental.1", readme)
        self.assertIn("releases/download/v0.2.0-experimental.1", readme)
        self.assertIn("Never substitute a checksum", readme)
        self.assertRegex(runbook, r"keep its output")
        self.assertIn("CURRENT", readme)
        self.assertIn("HISTORY", readme)
        self.assertIn("REVIEW", readme)
        self.assertIn("UNKNOWN", readme)
        self.assertIn("licensed under Apache License 2.0", readme)
        self.assertIn("the zipapp includes", readme)
        self.assertNotIn("no LICENSE", readme)
        self.assertIn("Experimental OSS", acceptance)
        self.assertNotRegex(combined, r"ghp_[A-Za-z0-9]{20,}")
        self.assertNotRegex(combined, r"github_pat_[A-Za-z0-9_]{20,}")
        self.assertNotRegex(combined, r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


if __name__ == "__main__":
    unittest.main()
