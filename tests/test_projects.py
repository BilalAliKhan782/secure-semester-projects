import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, directory):
    project = ROOT / directory
    sys.path.insert(0, str(project))
    try:
        spec = importlib.util.spec_from_file_location(name, project / "app.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class VoiceSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_module("voice_v2_app", "voice-v2")

    def test_passwords_are_salted_and_verified(self):
        first = self.app.hash_password("a secure password")
        second = self.app.hash_password("a secure password")
        self.assertNotEqual(first, second)
        self.assertTrue(self.app.verify_password("a secure password", first))
        self.assertFalse(self.app.verify_password("wrong password", first))

    def test_username_cannot_be_a_path(self):
        self.assertIsNotNone(self.app.USERNAME_RE.fullmatch("valid_user-1"))
        self.assertIsNone(self.app.USERNAME_RE.fullmatch("../escape"))


class NetShieldSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_module("netshield_v2_app", "netshield-v2")

    def test_safe_firewall_rule_is_parsed(self):
        command = (
            'netsh advfirewall firewall add rule name="Block_Test" '
            "dir=in action=block protocol=TCP localport=443"
        )
        args, name = self.app.parse_firewall_command(command)
        self.assertEqual(name, "Block_Test")
        self.assertEqual(args[0], "netsh")

    def test_shell_payloads_are_rejected(self):
        payloads = [
            "cmd /c whoami",
            'netsh advfirewall firewall add rule name="Bad" dir=in action=block & whoami',
            'netsh advfirewall firewall add rule name="Bad Name" dir=in action=block',
            'netsh advfirewall firewall add rule name="Bad" dir=in action=block localport=70000',
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises((TypeError, ValueError)):
                    self.app.parse_firewall_command(payload)


class StudentNlqSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_module = load_module("student_nlq_app", "student-nlq")
        cls.client = cls.app_module.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.app_module.mongo_client.close()

    def test_security_headers_and_no_debug_plan(self):
        response = self.client.post("/api/chat", json={"message": "help"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json["debug"])
        self.assertIn("Content-Security-Policy", response.headers)

    def test_long_messages_are_rejected(self):
        response = self.client.post("/api/chat", json={"message": "x" * 501})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
