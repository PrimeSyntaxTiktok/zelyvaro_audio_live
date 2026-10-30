"""Output formats and the clipboard dialog shared by all copy-link entry points."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QRadioButton,
                               QButtonGroup, QDialogButtonBox)

FORMATS = {
    'portrait': ('Portrait', 1080, 1920, '9:16'),
    'landscape': ('Paysage', 1920, 1080, '16:9'),
}


class StreamFormatDialog(QDialog):
    def __init__(self, selected='portrait', parent=None):
        super().__init__(parent)
        self.setWindowTitle('Format du lien TikTok / OBS')
        self.setMinimumWidth(420)
        self.setStyleSheet('QDialog{background:#0b1220;color:#e8edf8} QLabel,QRadioButton{color:#e8edf8} QRadioButton{padding:14px;background:#152035;border-radius:9px} QPushButton{padding:9px 15px}')
        layout = QVBoxLayout(self)
        title = QLabel('Choisir le format de diffusion')
        title.setStyleSheet('font-size:18px;font-weight:600;padding:8px 0')
        layout.addWidget(title)
        self.group = QButtonGroup(self)
        self.choices = {}
        for key, (label, width, height, ratio) in FORMATS.items():
            choice = QRadioButton(f'{label}  ·  {ratio}  ·  {width} × {height}')
            choice.setObjectName(key)
            self.group.addButton(choice)
            self.choices[key] = choice
            layout.addWidget(choice)
        self.choices[selected if selected in FORMATS else 'portrait'].setChecked(True)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet('color:#b7c7df;padding:10px 0')
        layout.addWidget(self.hint)
        self.group.buttonToggled.connect(lambda *_: self.update_hint())
        self.update_hint()
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Copier le lien')
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Annuler')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    @property
    def selected_format(self):
        return next(key for key, choice in self.choices.items() if choice.isChecked())

    def update_hint(self):
        _, width, height, _ = FORMATS[self.selected_format]
        self.hint.setText(f'Dans TikTok Studio ou OBS, régler la source Navigateur à {width} × {height} pour remplir le cadre. Le lien conserve ce format ; une autre taille affiche des bandes sans étirer la scène. Le logiciel de live garde le contrôle des dimensions de sa source.')
