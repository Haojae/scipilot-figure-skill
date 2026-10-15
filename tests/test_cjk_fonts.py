"""Regression tests for regular CJK face selection; no network required."""
from pathlib import Path
import sys, unittest
from unittest.mock import patch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ft2font import FT2Font
from matplotlib import font_manager as fm
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import setup_style as style

class CjkFontTests(unittest.TestCase):

    def tearDown(self):
        plt.close('all')
        plt.rcdefaults()

    def test_thin_face_rejected(self):

        class Face:
            style_name = 'Thin'
        with patch.object(style.fm, 'findfont', return_value='mock-font.ttf'), patch.object(style, 'FT2Font', return_value=Face()):
            self.assertFalse(style._has_regular_face('Mock CJK'))

    def test_regular_face_accepted(self):

        class Face:
            style_name = 'Regular'
        with patch.object(style.fm, 'findfont', return_value='mock-font.ttf'), patch.object(style, 'FT2Font', return_value=Face()):
            self.assertTrue(style._has_regular_face('Mock CJK'))

    def test_chinese_fallback_is_not_thin(self):
        plt.rcdefaults()
        try:
            result = style.setup_style(lang='zh', use_sciplots=False)
        except RuntimeError:
            self.skipTest('此机器未安装可用中文字体')
        face = FT2Font(fm.findfont(fm.FontProperties())).style_name.lower()
        self.assertNotIn('thin', face)
        self.assertTrue(style._has_regular_face(result['cjk_font']))


    def test_thin_family_falls_back_to_next_candidate(self):
        with patch.object(style, '_available_fonts', return_value={'Noto Sans SC','SimHei'}), patch.object(style, '_has_regular_face', side_effect=lambda f: f=='SimHei'):
            self.assertEqual(style.configure_chinese_fonts(), 'SimHei')

    def test_missing_regular_face_has_clear_error(self):
        with patch.object(style, '_available_fonts', return_value={'Noto Sans SC'}), patch.object(style, '_has_regular_face', return_value=False):
            with self.assertRaisesRegex(RuntimeError, '常规字重'):
                style.configure_chinese_fonts()

if __name__ == '__main__':
    unittest.main(verbosity=2)
