"""Targeted static regression checks, not a Shadowrocket parser."""
from pathlib import Path
import json
import re
import subprocess
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = "9ff0cc1"
BLOCKS = ("CONSERVATIVE ADBLOCK", "DOMESTIC APP ROUTING")
DOMESTIC = {"api-access.pangolin-sdk-toutiao.com", "mi.gdt.qq.com"}
OVERSEAS = {"googleads.g.doubleclick.net", "pagead2.googlesyndication.com",
            "securepubads.g.doubleclick.net"}
DIRECT = {"taobao.com", "jd.com", "360buyimg.com", "meituan.com", "meituan.net"}


def baseline(name):
    return subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)


def block(text, name):
    begin, end = f"# BEGIN {name}\n", f"# END {name}\n\n"
    return text[text.index(begin):text.index(end) + len(end)]


def active(text):
    return [s for s in text.splitlines() if s and not s.startswith("#")]


class AdblockingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "lazy_group.conf").read_text()
        cls.ads = block(cls.text, BLOCKS[0])
        cls.routing = block(cls.text, BLOCKS[1])

    def test_original_configuration_is_byte_identical_outside_additions(self):
        restored = self.text.replace(self.ads, "").replace(self.routing, "")
        self.assertEqual(restored.encode(), baseline("lazy_group.conf"))
        self.assertEqual((ROOT / "lazy.conf").read_bytes(), baseline("lazy.conf"))

    def test_exact_domains_and_partition(self):
        for region, hosts in (("DOMESTIC", DOMESTIC), ("OVERSEAS", OVERSEAS)):
            part = self.ads.split(f"# BEGIN {region} ADS\n")[1].split(f"# END {region} ADS")[0]
            self.assertEqual(set(active(part)), {f"DOMAIN,{h},REJECT" for h in hosts})
        self.assertEqual(len(active(self.ads)), len(DOMESTIC | OVERSEAS))
        self.assertEqual(set(active(self.routing)), {f"DOMAIN-SUFFIX,{h},DIRECT" for h in DIRECT})
        for rule in active(self.ads) + active(self.routing):
            self.assertEqual(self.text.splitlines().count(rule), 1)
            self.assertRegex(rule, r"^DOMAIN(?:-SUFFIX)?,[a-z0-9]+(?:[.-][a-z0-9]+)*,(?:REJECT|DIRECT)$")

    def test_priority_ads_then_domestic_then_existing_services(self):
        section = self.text.split("[Rule]\n", 1)[1]
        self.assertEqual(active(section.split(self.ads)[0]), [])
        self.assertLess(self.text.index(self.ads), self.text.index(self.routing))
        self.assertEqual(active(self.text.split(self.ads)[1].split(self.routing)[0]), [])
        self.assertIn("RULE-SET,", self.text.split(self.routing)[1])

    def test_ad_host_boundaries(self):
        hosts = {s.split(",")[1] for s in active(self.ads)}
        for host in DOMESTIC | OVERSEAS:
            self.assertIn(host, hosts)
            for other in ("sub." + host, "not" + host, host + ".example.org"):
                self.assertNotIn(other, hosts)
        for host in ("acs.m.taobao.com", "api.m.jd.com", "wmapi.meituan.com",
                     "apimobile.meituan.com", "img.meituan.net", "www.google.com",
                     "accounts.google.com", "www.gstatic.com", "api.openai.com",
                     "youtubei.googleapis.com", "rr1.googlevideo.com", "www.youtube.com",
                     "x.com", "api.x.com", "api.twitter.com", "video.twimg.com",
                     "www.paypal.com", "login.microsoftonline.com"):
            self.assertNotIn(host, hosts)

    def test_domestic_routing_suffix_boundaries(self):
        suffixes = {s.split(",")[1] for s in active(self.routing)}
        def direct(host):
            return any(host == s or host.endswith("." + s) for s in suffixes)
        for domain in DIRECT:
            self.assertTrue(direct(domain))
            self.assertTrue(direct("api." + domain))
            self.assertFalse(direct("not" + domain))
            self.assertFalse(direct(domain + ".example.org"))
        for host in ("www.youtube.com", "api.x.com", "api.openai.com"):
            self.assertFalse(direct(host))

    def test_independent_disable_and_full_rollback(self):
        # Disabling one ad partition must retain the other and the domestic routing.
        for region, remaining in (("DOMESTIC", OVERSEAS), ("OVERSEAS", DOMESTIC)):
            part = self.ads.split(f"# BEGIN {region} ADS\n")[1].split(f"# END {region} ADS")[0]
            disabled = self.text.replace(part, "\n")
            new_ads = active(block(disabled, BLOCKS[0]))
            self.assertEqual(set(new_ads), {f"DOMAIN,{h},REJECT" for h in remaining})
            self.assertEqual(block(disabled, BLOCKS[1]), self.routing)
        disabled = self.text
        for rule in active(self.ads) + active(self.routing):
            disabled = disabled.replace("\n" + rule + "\n", "\n# " + rule + "\n")
        def rules(text):
            return active(text.split("[Rule]\n", 1)[1].split("\n[", 1)[0])
        self.assertEqual(rules(disabled), rules(baseline("lazy_group.conf").decode()))


class OptionalModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads((ROOT / "tests/fixtures/adblocking_urls.json").read_text())

    def load_module(self, name):
        text = (ROOT / f"modules/adblocking/{name}.sgmodule").read_text()
        rewrite = text.split("[URL Rewrite]\n", 1)[1].split("\n[MITM]", 1)[0]
        rules = [s.rsplit(" - ", 1) for s in active(rewrite)]
        hosts = text.split("hostname = %APPEND% ", 1)[1].strip().split(",")
        return text, [(re.compile(p), action) for p, action in rules], hosts

    def test_positive_negative_and_adversarial_urls(self):
        for name, item in self.fixtures.items():
            _, rules, _ = self.load_module(name)
            for url in item["positive"]:
                with self.subTest(module=name, positive=url):
                    self.assertEqual(sum(bool(p.search(url)) for p, _ in rules), 1)
                parsed = urlsplit(url)
                # Same path on an unrelated host, spoofed host, or insecure scheme.
                for host in ("example.org", parsed.netloc + ".example.org", "not" + parsed.netloc):
                    spoof = url.replace(parsed.netloc, host, 1)
                    self.assertFalse(any(p.search(spoof) for p, _ in rules))
                self.assertFalse(any(p.search(url.replace("https://", "http://", 1)) for p, _ in rules))
            for url in item["negative"]:
                with self.subTest(module=name, negative=url):
                    self.assertFalse(any(p.search(url) for p, _ in rules))

    def test_minimal_mitm_scope_and_no_remote_code_or_credentials(self):
        for name, item in self.fixtures.items():
            text, rules, hosts = self.load_module(name)
            self.assertEqual(hosts, item["hosts"])
            self.assertTrue(all("*" not in h for h in hosts))
            self.assertEqual(re.findall(r"^\[([^]]+)\]$", text, re.M), ["URL Rewrite", "MITM"])
            for forbidden in ("script-path", "ca-p12", "ca-passphrase", "enable =", "skip-cert-verify"):
                self.assertNotIn(forbidden, text)
            for pattern, action in rules:
                self.assertIn(action, ("reject", "reject-dict", "reject-200"))
                matches = [u for u in item["positive"] if pattern.search(u)]
                self.assertTrue(matches)
                for url in matches:
                    self.assertIn(urlsplit(url).hostname, hosts)
        # Optional module URLs and hostnames are not added to the main MITM section.
        mitm = (ROOT / "lazy_group.conf").read_text().split("[MITM]", 1)[1]
        self.assertNotIn("sgmodule", (ROOT / "lazy_group.conf").read_text())
        for item in self.fixtures.values():
            for host in item["hosts"]:
                self.assertNotIn(host, mitm)


if __name__ == "__main__":
    unittest.main()
