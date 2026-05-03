from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tor_llm_tool.settings.config import TaskPresetConfig, default_task_presets


class TaskPresetsDialog(QDialog):
    def __init__(self, presets: list[TaskPresetConfig], parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Task Presets")
        self.resize(560, 360)
        self.rows: list[tuple[QCheckBox, QLineEdit, str]] = []

        rows_layout = QVBoxLayout()
        for preset in presets:
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            enabled = QCheckBox()
            enabled.setChecked(preset.enabled)
            label = QLineEdit(preset.label)
            row.addWidget(enabled)
            row.addWidget(QLabel(preset.task_id))
            row.addWidget(label, 1)
            rows_layout.addWidget(row_widget)
            self.rows.append((enabled, label, preset.task_id))

        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self.reset_defaults)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(reset_button)
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(rows_layout)
        layout.addLayout(buttons)

    def updated_presets(self) -> list[TaskPresetConfig]:
        presets = []
        for enabled, label, task_id in self.rows:
            presets.append(
                TaskPresetConfig(id=task_id, label=label.text().strip() or task_id, enabled=enabled.isChecked())
            )
        return presets

    def reset_defaults(self) -> None:
        for row, preset in zip(self.rows, default_task_presets(), strict=False):
            enabled, label, _task_id = row
            enabled.setChecked(preset.enabled)
            label.setText(preset.label)
