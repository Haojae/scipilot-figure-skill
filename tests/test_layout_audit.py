"""Regression tests for clipping audit; no network or image files required."""
from pathlib import Path
import sys, unittest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from visual_qa import audit_layout

class LayoutAuditTests(unittest.TestCase):

    def tearDown(self):
        plt.close('all')
        plt.rcdefaults()

    def test_contained_labels_after_temporary_save_dpi(self):
        for family in ['DejaVu Sans', 'Microsoft YaHei']:
            if family not in {f.name for f in fm.fontManager.ttflist}:
                continue
            plt.rcdefaults()
            plt.rcParams.update({'font.family': family, 'font.size': 11, 'axes.labelsize': 12})
            fig, ax = plt.subplots(figsize=(8, 5), dpi=150, layout='constrained')
            ax.plot([1990, 2024], [12000, 40000])
            ax.set(xlabel='Year', ylabel='GDP per capita (constant 2021 international $, PPP)')
            issues = audit_layout(fig)
            self.assertFalse(any(('超出画布' in msg for _, msg in issues)), (family, issues))
            plt.close(fig)

    def test_clipped_ticks_are_reported(self):
        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        fig.subplots_adjust(left=0.12, bottom=0.22)
        ax.set_yticks([0, 0.5, 1], ['Excessively long region name A', 'Excessively long region name B', 'Excessively long region name C'])
        ax.set_ylim(0, 1)
        issues = audit_layout(fig)
        self.assertTrue(any(('超出画布' in msg for _, msg in issues)), issues)

    def test_genuine_axis_label_clip_is_still_reported(self):
        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        ax.set_ylabel('A genuinely clipped label')
        ax.yaxis.set_label_coords(-1.5, 0.5)
        issues = audit_layout(fig)
        self.assertTrue(any(('超出画布' in msg for _, msg in issues)), issues)

    def test_ticks_outside_view_are_not_clipping_errors(self):
        fig, ax = plt.subplots(figsize=(5,3),dpi=150,layout='constrained')
        ax.set_xlim(0,1)
        ax.set_ylim(0,1)
        ax.set_xticks([-10,0,.5,1,10],['Invisible left','0','0.5','1','Invisible right'])
        ax.set_xlim(0,1)
        issues=audit_layout(fig)
        self.assertFalse(any('超出画布' in msg for _,msg in issues),issues)

    def test_clipped_chinese_ticks_when_font_available(self):
        families={f.name for f in fm.fontManager.ttflist}
        family=next((f for f in ['Microsoft YaHei','SimHei','Noto Sans CJK SC'] if f in families),None)
        if family is None:
            self.skipTest('No CJK font installed')
        plt.rcParams['font.family']=[family]
        fig,ax=plt.subplots(figsize=(5,3),dpi=100)
        fig.subplots_adjust(left=.12,bottom=.22)
        ax.set_yticks([0,.5,1],['超出画布边界的很长地区名称甲','超出画布边界的很长地区名称乙','超出画布边界的很长地区名称丙'])
        ax.set_ylim(0,1)
        issues=audit_layout(fig)
        self.assertTrue(any('超出画布' in msg for _,msg in issues),issues)

if __name__=='__main__':
    unittest.main(verbosity=2)
