"""Exact, opaque delivery through inert HTML text, including renderer rewrites."""
from html import unescape
import base64
import json
import random
import re
import shutil
import subprocess
import unittest
from build_kitchen_mobile_preview import mobile_page
from build_miniature_kitchen_preview import (
    BASE85_DECODER_JS, DELIVERY_LIMIT, PACKED_MARKER, SAFE_BASE85_ALPHABET,
    decode_base85, encode_base85, fit_document, pack_document, unpack_document)


class KitchenMobileTransport(unittest.TestCase):
    def test_inner_document_roundtrips_without_changing_quotes_unicode_or_script_case(self):
        content = '''<!doctype html><html lang="ko"><body>우유 &amp; '두부'
<script>const value = "한 끼"; const raw = "\\\\n</template>&notit;&#13;";</ScRiPt><!-- <script> -->
</body></html>'''+'\r\n끝\r다음'
        wrapper = mobile_page(content, 'app')
        match = re.search(r'<template id="kitchenSource">(.*?)</template>', wrapper, re.S)
        self.assertIsNotNone(match)
        payload = match.group(1)
        self.assertEqual(unescape(payload), content)
        self.assertNotRegex(payload, r'(?i)</script')
        self.assertNotIn('<!--', payload)
        self.assertNotIn('<', payload)
        self.assertIn('sandbox="allow-scripts allow-forms"', wrapper)
        self.assertNotIn('allow-same-origin', wrapper)
        rewritten = re.sub(r'<script', '<script type="text/htmlpreview"', wrapper, flags=re.I)
        transported = re.search(r'<template id="kitchenSource">(.*?)</template>', rewritten, re.S).group(1)
        self.assertEqual(unescape(transported), content)

    def test_actual_modes_keep_accessible_frame_titles(self):
        for mode, name in [('app', '앱'), ('widget', '위젯')]:
            wrapper = mobile_page('<p>기록</p>', mode)
            self.assertIn(f'title="한끼의 부엌 {name} 미리보기"', wrapper)
            self.assertIn('.content.textContent', wrapper)
            self.assertNotIn('JSON.parse(', wrapper)

    def test_null_is_rejected_instead_of_silently_replacing_source_text(self):
        with self.assertRaisesRegex(ValueError, 'null character'):
            mobile_page('<p>우유\0</p>', 'widget')

    def test_packed_html_is_deterministic_exact_utf8_and_keeps_each_asset_byte(self):
        assets = ['data:image/webp;base64,'+base64.b64encode(bytes(range(i, i+64))).decode()
                  for i in range(8)]
        original = '\ufeff<!doctype html><html lang="ko"><style>p:before{content:"< & \\\\";}</style>'
        original += '<body>한 끼 &amp; &#13; </template>\r\n'+' '.join(assets)
        original += '<script>const value="한 끼";</script></body></html>'
        packed = pack_document(original, 'widget')
        self.assertEqual(pack_document(original, 'widget'), packed)
        self.assertEqual(unpack_document(packed).encode('utf-8'), original.encode('utf-8'))
        self.assertEqual(pack_document(packed, 'widget'), packed)
        decoded_assets = re.findall(r'data:image/webp;base64,[A-Za-z0-9+/=]+', unpack_document(packed))
        self.assertEqual(decoded_assets, assets)

    def test_only_oversized_html_uses_the_fallback_without_raising_the_cap(self):
        small = '<p>오늘의 부엌</p>'
        self.assertEqual(fit_document(small, 'widget'), small)
        large = '<!doctype html><body><!--'+('한 끼의 부엌 '*100000)+'--></body>'
        self.assertGreater(len(large.encode('utf-8')), DELIVERY_LIMIT)
        delivered = fit_document(large, 'widget')
        self.assertIn(PACKED_MARKER, delivered)
        self.assertLessEqual(len(delivered.encode('utf-8')), DELIVERY_LIMIT)
        self.assertEqual(unpack_document(delivered), large)
        self.assertEqual(fit_document(delivered, 'widget'), delivered)

    def test_corrupt_truncated_and_mismatched_packed_source_is_rejected(self):
        packed = pack_document('<html><body>같은 원문</body></html>')
        payload = re.search(r'data-sha256="[0-9a-f]{64}">([A-Za-z0-9+/=]+)</template>', packed).group(1)
        damaged = [packed.replace(payload, payload[:-8]),
                   packed.replace(payload, '!'+payload[1:]),
                   re.sub(r'data-bytes="\d+"', 'data-bytes="1"', packed),
                   re.sub(r'data-sha256="[0-9a-f]{64}"', 'data-sha256="'+('0'*64)+'"', packed)]
        for content in damaged:
            with self.subTest(content=content[-80:]):
                with self.assertRaises(ValueError):
                    unpack_document(content)

    def test_pack_decoder_is_self_contained_and_needs_no_streaming_api(self):
        packed = pack_document('<p>부엌</p>')
        self.assertNotRegex(packed, r'\b(?:fetch|Worker|XMLHttpRequest|DecompressionStream)\b')
        self.assertNotRegex(packed, r'<script[^>]+src=')
        self.assertIn('DOMContentLoaded', packed)
        self.assertIn('document.open();document.write(html);document.close();', packed)
        wrapper = mobile_page(packed, 'widget')
        payload = re.search(r'<template id="kitchenSource">(.*?)</template>', wrapper, re.S).group(1)
        self.assertEqual(unescape(payload), packed)
        self.assertIn('sandbox="allow-scripts allow-forms"', wrapper)
        self.assertNotIn('allow-same-origin', wrapper)

    def test_base85_roundtrips_all_bytes_and_partial_groups_with_safe_html_digits(self):
        self.assertEqual(len(SAFE_BASE85_ALPHABET), 85)
        self.assertEqual(len(set(SAFE_BASE85_ALPHABET)), 85)
        for length in range(261):
            data = bytes(index % 256 for index in range(length))
            encoded = encode_base85(data)
            self.assertEqual(decode_base85(encoded), data)
            self.assertNotRegex(encoded, '[&<>]')
            self.assertTrue(set(encoded).issubset(SAFE_BASE85_ALPHABET))

    def test_base85_packed_source_is_deterministic_exact_unicode_and_legacy_compatible(self):
        original = '\ufeff<!doctype html><html lang="ko"><body>\r\n'
        original += '<p>사진 &amp; 우유 525mL · 🥚</p></template>\r'
        original += '<script>const text="한 끼";</script></body></html>'
        packed = pack_document(original, 'widget', codec='gzip-base85')
        self.assertEqual(packed, pack_document(original, 'widget', codec='gzip-base85'))
        self.assertIn('data-codec="gzip-base85"', packed)
        self.assertEqual(unpack_document(packed).encode('utf-8'), original.encode('utf-8'))
        self.assertEqual(pack_document(packed, 'widget', codec='gzip-base85'), packed)
        old = pack_document(original, 'widget')
        self.assertIn('data-codec="gzip-base64"', old)
        self.assertEqual(unpack_document(old), original)
        payload = re.search(r'data-sha256="[0-9a-f]{64}">([^<]*)</template>', packed).group(1)
        self.assertNotRegex(payload, '[&<>]')
        payload = re.search(r'<template id="kitchenSource">(.*?)</template>',
                            mobile_page(packed, 'widget'), re.S).group(1)
        self.assertEqual(unescape(payload), packed)

    def test_base85_corruption_length_hash_and_codec_errors_are_rejected(self):
        packed = pack_document('<p>원본과 같은 기록</p>', codec='gzip-base85')
        payload = re.search(r'data-sha256="[0-9a-f]{64}">([^<]*)</template>', packed).group(1)
        for damaged in [packed.replace(payload, '&'+payload[1:]),
                        packed.replace(payload, payload[:-4]),
                        packed.replace(payload, '0'),
                        packed.replace('gzip-base85', 'gzip-unknown'),
                        re.sub(r'data-bytes="\d+"', 'data-bytes="1"', packed),
                        re.sub(r'data-sha256="[0-9a-f]{64}"', 'data-sha256="'+('0'*64)+'"', packed)]:
            with self.subTest(damaged=damaged[-70:]):
                with self.assertRaises(ValueError):
                    unpack_document(damaged)
        for value in ['0', '&', '<', '>', ' ', '~~~~~']:
            with self.assertRaises(ValueError):
                decode_base85(value)

    def test_real_incompressible_html_fits_base85_when_base64_exceeds_the_same_cap(self):
        data = random.Random(1103).randbytes(800000)
        original = '<!doctype html><body><p>'+base64.b64encode(data).decode()+'</p></body>'
        self.assertGreater(len(pack_document(original).encode()), DELIVERY_LIMIT)
        delivered = fit_document(original)
        self.assertIn('data-codec="gzip-base85"', delivered)
        self.assertLessEqual(len(mobile_page(delivered, 'app').encode()), DELIVERY_LIMIT)
        self.assertEqual(unpack_document(delivered), original)

    @unittest.skipUnless(shutil.which('node'), 'JavaScript runtime is not installed')
    def test_actual_javascript_base85_decoder_matches_all_byte_values_and_partial_groups(self):
        cases = [bytes(index % 256 for index in range(length)) for length in range(261)]
        script = BASE85_DECODER_JS + '''
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(input.map(value=>Array.from(decodeBase85(value)))));
'''
        result = subprocess.run([shutil.which('node'), '-e', script],
                                input=json.dumps([encode_base85(data) for data in cases]),
                                text=True, check=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout), [list(data) for data in cases])


if __name__ == '__main__':
    unittest.main()
