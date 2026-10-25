import re
import shutil
import subprocess
import unittest
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "frontend" / "dashboard.html"


class DashboardNotificationSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DASHBOARD.read_text(encoding="utf-8")

    def test_html_escape_helper_encodes_dangerous_characters(self):
        helper = re.search(
            r"function escapeHtml\(value\)\s*\{(.*?)\n\}",
            self.source,
            re.DOTALL,
        )
        self.assertIsNotNone(helper, "escapeHtml helper is missing")

        body = helper.group(1)
        for expected in (
            "String(value ?? \"\")",
            "&amp;",
            "&lt;",
            "&gt;",
            "&quot;",
            "&#39;",
        ):
            self.assertIn(expected, body)

    def test_notification_fields_are_escaped_before_html_interpolation(self):
        expected_interpolations = (
            r'data-notification-id="\$\{escapeHtml\(notification\.id\)\}"',
            r'data-notification-type="\$\{escapeHtml\(notification\.type\)\}"',
            r'data-reference-type="\$\{escapeHtml\(notification\.reference_type \|\| ""\)\}"',
            r'data-reference-id="\$\{escapeHtml\(notification\.reference_id \|\| ""\)\}"',
            r'<span>\$\{escapeHtml\(notification\.title\)\}</span>',
            r'\$\{escapeHtml\(notification\.message\)\}',
            r'\$\{escapeHtml\(formatNotificationTime\(notification\.created_at\)\)\}',
        )

        for pattern in expected_interpolations:
            with self.subTest(pattern=pattern):
                self.assertRegex(self.source, pattern)

    def test_hostile_text_is_encoded_as_text(self):
        hostile = '<img src=x onerror="alert(1)">&\''
        escaped = (
            hostile.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

        self.assertNotIn("<img", escaped)
        self.assertNotIn('="alert(1)"', escaped)
        self.assertEqual(unescape(escaped), hostile)


    def test_actual_javascript_helper_with_node(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")

        script = r"""
const fs = require("fs");
const vm = require("vm");
const assert = require("assert/strict");

const html = fs.readFileSync(process.argv[1], "utf8");
const match = html.match(
    /function escapeHtml\(value\)\s*\{[\s\S]*?\n\}/
);
assert.ok(match, "escapeHtml() must exist");

const context = {};
vm.runInNewContext(
    `${match[0]}; this.escapeHtml = escapeHtml;`,
    context
);

const cases = [
    [
        '<img src=x onerror="alert(1)">',
        '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'
    ],
    [
        `Tom & Jerry's "exam"`,
        'Tom &amp; Jerry&#39;s &quot;exam&quot;'
    ],
    [null, ""],
    [123, "123"]
];

for (const [input, expected] of cases) {
    assert.equal(context.escapeHtml(input), expected);
}
"""

        result = subprocess.run(
            [node, "-e", script, str(DASHBOARD)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr or result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
