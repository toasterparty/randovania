import dataclasses

from PySide6 import QtCore

from randovania.game_description.game_description import GameDescription
from randovania.games.prime2.layout.hint_configuration import ItemHintMode, LocationHintMode, HintConfiguration
from randovania.gui.generated.preset_echoes_hints_ui import Ui_PresetEchoesHints
from randovania.gui.lib.common_qt_lib import set_combo_with_value
from randovania.gui.lib.window_manager import WindowManager
from randovania.gui.preset_settings.preset_tab import PresetTab
from randovania.interface_common.preset_editor import PresetEditor
from randovania.layout.preset import Preset


class PresetEchoesHints(PresetTab, Ui_PresetEchoesHints):
    def __init__(self, editor: PresetEditor, game_description: GameDescription, window_manager: WindowManager):
        super().__init__(editor, game_description, window_manager)
        self.setupUi(self)

        self.hint_layout.setAlignment(QtCore.Qt.AlignTop)

        for i, mode in enumerate(ItemHintMode):
            self.stk_combo.setItemData(i, mode)
            self.translator_combo.setItemData(i, mode)

        for i, mode in enumerate(LocationHintMode):
            self.dark_temple_combo.setItemData(i, mode)
            self.twomos_combo.setItemData(i, mode)

        self.stk_combo.currentIndexChanged.connect(self._on_stk_combo_changed)
        self.translator_combo.currentIndexChanged.connect(self._on_translator_combo_changed)
        self.dark_temple_combo.currentIndexChanged.connect(self._on_dark_temple_combo_changed)
        self.twomos_combo.currentIndexChanged.connect(self._on_twomos_combo_changed)

        self.lore_checkbox.stateChanged.connect(self._persist_option_then_notify("use_lore_scans"))
        self.keybearer_checkbox.stateChanged.connect(self._persist_option_then_notify("use_keybearer_scans"))
        self.translator_checkbox.stateChanged.connect(
            self._persist_option_then_notify("translators_on_energy_controllers"))

    @classmethod
    def tab_title(cls) -> str:
        return "Hints"

    @classmethod
    def uses_patches_tab(cls) -> bool:
        return False

    def _on_stk_combo_changed(self, new_index: int):
        with self._editor as editor:
            editor.set_configuration_field(
                "hints",
                dataclasses.replace(editor.configuration.hints,
                                    sky_temple_keys=self.stk_combo.currentData()))

    def _on_translator_combo_changed(self, new_index: int):
        with self._editor as editor:
            editor.set_configuration_field(
                "hints",
                dataclasses.replace(editor.configuration.hints,
                                    translators=self.translator_combo.currentData()))

    def _on_dark_temple_combo_changed(self, new_index: int):
        with self._editor as editor:
            editor.set_configuration_field(
                "hints",
                dataclasses.replace(editor.configuration.hints,
                                    dark_temples=self.dark_temple_combo.currentData()))

    def _on_twomos_combo_changed(self, new_index: int):
        with self._editor as editor:
            editor.set_configuration_field(
                "hints",
                dataclasses.replace(editor.configuration.hints,
                                    light_suit_location=self.twomos_combo.currentData()))

    def on_preset_changed(self, preset: Preset):
        set_combo_with_value(self.stk_combo, preset.configuration.hints.sky_temple_keys)
        set_combo_with_value(self.translator_combo, preset.configuration.hints.translators)
        set_combo_with_value(self.dark_temple_combo, preset.configuration.hints.dark_temples)
        set_combo_with_value(self.twomos_combo, preset.configuration.hints.light_suit_location)
        
        self.lore_checkbox.setChecked(preset.configuration.hints.use_lore_scans)
        self.keybearer_checkbox.setChecked(preset.configuration.hints.use_keybearer_scans)
        self.translator_checkbox.setChecked(preset.configuration.hints.translators_on_energy_controllers)
