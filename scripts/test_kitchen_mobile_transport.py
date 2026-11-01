"""Exact, opaque delivery of the kitchen document through a compact JSON wrapper."""
import json
import re
import unittest
from build_kitchen_mobile_preview import mobile_page


class KitchenMobileTransport(unittest.TestCase):
    def test_inner_document_roundtrips_without_changing_quotes_unicode_or_script_case(self):
        content = '''<!doctype html><html lang="ko"><body>우유 &amp; '두부'
<script>const value = "한 끼";</ScRiPt><!-- <script> --></body></html>'''
        wrapper = mobile_page(content, 'app')
        match = re.search(r'<template id="kitchenSource">(.*?)</template>', wrapper, re.S)
        self.assertIsNotNone(match)
        payload = match.group(1)
        self.assertEqual(json.loads(payload), content)
        self.assertNotRegex(payload, r'(?i)</script')
        self.assertNotIn('<!--', payload)
        self.assertNotIn('<', payload)
        self.assertNotIn('&', payload)
        self.assertIn('sandbox="allow-scripts allow-forms"', wrapper)
        self.assertNotIn('allow-same-origin', wrapper)
        rewritten = re.sub(r'<script', '<script type="text/htmlpreview"', wrapper, flags=re.I)
        transported = re.search(r'<template id="kitchenSource">(.*?)</template>', rewritten, re.S).group(1)
        self.assertEqual(json.loads(transported), content)

    def test_actual_modes_keep_accessible_frame_titles(self):
        for mode, name in [('app', '앱'), ('widget', '위젯')]:
            wrapper = mobile_page('<p>기록</p>', mode)
            self.assertIn(f'title="한끼의 부엌 {name} 미리보기"', wrapper)
            self.assertIn('JSON.parse(', wrapper)


if __name__ == '__main__':
    unittest.main()
