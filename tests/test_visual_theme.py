"""Lightweight theme contract tests (no graphical display required)."""
import ast
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parents[1]


def test_shared_theme_has_widget_and_interaction_states():
    theme = config.STYLESHEET
    for selector in ('QFrame#Card', 'QFrame#StatCard', 'QFrame#FilterCard',
                     'alternate-background-color', 'QPushButton#FilterChip:checked',
                     'QSpinBox', 'QPushButton:disabled', 'QLineEdit:focus'):
        assert selector in theme
    assert 'QFrame#LoginCard' in config.LOGIN_STYLESHEET
    assert 'QPushButton#PrimaryButton:disabled' in config.LOGIN_STYLESHEET


def test_all_ui_modules_compile_and_dialogs_do_not_replace_theme():
    for path in ROOT.glob('ui_*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        if path.name not in ('ui_dashboard.py', 'ui_login.py'):
            assert 'self.setStyleSheet(' not in path.read_text(encoding='utf-8')


def test_fleet_documents_cards_use_scoped_styles_and_wrapping():
    source = (ROOT / 'ui_crew_documents.py').read_text(encoding='utf-8')
    fleet = source.split('class FleetDocumentsDialog(QDialog):', 1)[1]
    assert 'frame.setObjectName({' in fleet
    assert 'frame.setStyleSheet(' not in fleet.split('def load_crew_list', 1)[0]
    assert 'QFrame {' not in fleet.split('def load_crew_list', 1)[0]
    assert 'filter_frame.setObjectName("FleetFilterCard")' in fleet
    assert 'filter_layout.addLayout(fields_row)' in fleet
    assert 'filter_layout.addLayout(search_row)' in fleet
    assert 'main_layout.addLayout(actions_layout)' in fleet
    assert 't_lbl.setWordWrap(True)' in fleet
