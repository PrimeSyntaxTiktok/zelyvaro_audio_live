"""Output formats and the clipboard dialog shared by all copy-link entry points."""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QRadioButton,
                               QButtonGroup, QDialogButtonBox)

FORMATS = {
    'portrait': ('Portrait', 2160, 3840, '9:16'),
    'landscape': ('Paysage', 3840, 2160, '16:9'),
}


def format_dimensions(mode, quality='4k'):
    label, width, height, ratio = FORMATS[mode]
    divisor = 2 if quality == '1080' else 1
    return label, width // divisor, height // divisor, ratio


class StreamFormatDialog(QDialog):
    def __init__(self, selected='portrait', parent=None, quality='4k'):
        super().__init__(parent)
        self.setWindowTitle('Format du lien TikTok / OBS')
        self.setMinimumWidth(420)
        self.quality = quality
        self.setStyleSheet('QDialog{background:#0b1220;color:#e8edf8} QLabel,QRadioButton{color:#e8edf8} QRadioButton{padding:14px;background:#152035;border-radius:9px} QPushButton{padding:9px 15px}')
        layout = QVBoxLayout(self)
        title = QLabel('Choisir le format de diffusion')
        title.setStyleSheet('font-size:18px;font-weight:600;padding:8px 0')
        layout.addWidget(title)
        self.group = QButtonGroup(self)
        self.choices = {}
        for key in FORMATS:
            label, width, height, ratio = format_dimensions(key, quality)
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
        _, width, height, _ = format_dimensions(self.selected_format, self.quality)
        self.hint.setText(f'Le rendu remplit toute la source, sans bandes ajoutées.\n\n'
                          f'Dans TikTok : ouvrir les propriétés du Lien, activer la résolution personnalisée et saisir {width} × {height}. Agrandir ensuite la source pour couvrir la scène.\n\n'
                          f'Dans OBS : régler Largeur {width}, Hauteur {height}, puis Transformation → Ajuster à l’écran.\n\n'
                          'Le lien ne peut pas agrandir lui-même un petit cadre placé dans TikTok ou OBS.')
