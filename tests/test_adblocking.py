"""Targeted static regression checks, not a Shadowrocket parser."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = "9ff0cc1"
BEGIN = "# BEGIN CONSERVATIVE ADBLOCK\n"
END = "# END CONSERVATIVE ADBLOCK\n\n"
HOSTS = {
    "googleads.g.doubleclick.net",
    "pagead2.googlesyndication.com",
    "securepubads.g.doubleclick.net",
}


def baseline(name):
    return subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)


class AdblockingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "lazy_group.conf").read_bytes()
        cls.text = cls.raw.decode()
        cls.start = cls.text.index(BEGIN)
        cls.stop = cls.text.index(END) + len(END)
        cls.block = cls.text[cls.start:cls.stop]
        cls.rules = [line for line in cls.block.splitlines()
                     if line and not line.startswith("#")]

    def test_original_configuration_is_byte_identical(self):
        restored = (self.text[:self.start] + self.text[self.stop:]).encode()
        self.assertEqual(restored, baseline("lazy_group.conf"))
        self.assertEqual((ROOT / "lazy.conf").read_bytes(), baseline("lazy.conf"))

    def test_supported_exact_domain_syntax_and_no_duplicates(self):
        self.assertEqual(len(self.rules), len(HOSTS))
        self.assertEqual(set(self.rules), {f"DOMAIN,{h},REJECT" for h in HOSTS})
        for rule in self.rules:
            self.assertRegex(rule, r"^DOMAIN,[a-z0-9]+(?:[.-][a-z0-9]+)*,REJECT$")
            self.assertEqual(self.text.splitlines().count(rule), 1)

    def test_rules_precede_all_original_active_rules(self):
        section = self.text[:self.start].rsplit("[", 1)[-1].split("]", 1)[0]
        self.assertEqual(section, "Rule")
        prefix = self.text.split("[Rule]\n", 1)[1].split(BEGIN, 1)[0]
        self.assertFalse([s for s in prefix.splitlines() if s and not s.startswith("#")])
        self.assertIn("RULE-SET,", self.text[self.stop:])

    def test_positive_and_boundary_cases(self):
        # Model only DOMAIN equality; all other decisions belong to existing rules.
        blocked = {rule.split(",")[1] for rule in self.rules}
        for host in HOSTS:
            with self.subTest(host=host):
                self.assertIn(host, blocked)
                for other in ("sub." + host, host + ".example.org", "not" + host):
                    self.assertNotIn(other, blocked)
        for host in ("doubleclick.net", "googlesyndication.com", "www.google.com",
                     "accounts.google.com", "www.gstatic.com", "googleapis.com",
                     "googleusercontent.com", "api.openai.com", "www.youtube.com",
                     "www.netflix.com", "www.paypal.com", "apple.com",
                     "login.microsoftonline.com", "localhost"):
            with self.subTest(host=host):
                self.assertNotIn(host, blocked)

    def test_disabling_rules_restores_original_active_rule_sequence(self):
        def active_rules(text):
            section = text.split("[Rule]\n", 1)[1].split("\n[", 1)[0]
            return [s for s in section.splitlines() if s and not s.startswith("#")]
        disabled = self.text
        for rule in self.rules:
            disabled = disabled.replace("\n" + rule + "\n", "\n# " + rule + "\n")
        self.assertEqual(active_rules(disabled), active_rules(baseline("lazy_group.conf").decode()))


if __name__ == "__main__":
    unittest.main()
