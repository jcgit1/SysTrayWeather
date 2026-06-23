from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from systrayweather.config import validate_location_query


class LocationDialog(QDialog):
    def __init__(self, current_query: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SysTrayWeather — Location")
        self.setModal(True)
        self.resize(400, 180)

        self._query_input = QLineEdit(current_query)
        self._query_input.setPlaceholderText("90210 or Austin")

        self._error = QLabel("")
        self._error.setStyleSheet("color: #e74c3c;")
        self._error.setWordWrap(True)

        intro = QLabel(
            "Enter a US zip code (e.g. 90210) or city name (e.g. Austin or Portland)."
        )
        intro.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Location:", self._query_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)

        self._location_query = ""

    @property
    def location_query(self) -> str:
        return self._location_query

    def _on_accept(self) -> None:
        error = validate_location_query(self._query_input.text())
        if error:
            self._error.setText(error)
            return
        self._location_query = self._query_input.text().strip()
        self.accept()
