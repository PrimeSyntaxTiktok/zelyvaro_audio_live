"""Audio application picker, using Windows render-session enumeration."""
from PySide6.QtCore import QFileInfo, Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QDialogButtonBox, QFileIconProvider)
from process_audio import applications, supported


class SourceDialog(QDialog):
    def __init__(self, selected, parent=None):
        super().__init__(parent)
        self.selected = selected
        self.setWindowTitle('Choisir la source audio')
        self.resize(420, 460)
        self.setStyleSheet('QDialog{background:#0b1220;color:#e8edf8} QLabel{color:#b4bfd3} QListWidget{background:#111c2e;color:#fff;border:1px solid #334159;border-radius:9px;padding:6px} QListWidget::item{padding:13px 8px} QListWidget::item:selected{background:#423765;border-radius:6px} QPushButton{padding:8px 13px}')
        layout = QVBoxLayout(self)
        title = QLabel('Quelle application doit animer votre décor ?')
        title.setStyleSheet('font-size:15px;font-weight:600;color:#fff;padding:8px 0')
        layout.addWidget(title)
        self.description = QLabel('Seul le son de l’application sélectionnée sera utilisé.\nLancez une musique si votre application n’apparaît pas.')
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
        self.list = QListWidget()
        layout.addWidget(self.list)
        refresh = QPushButton('Actualiser les applications')
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Utiliser cette source')
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Annuler')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.buttons)
        self.refresh()

    def refresh(self):
        choice = self.list.currentItem()
        wanted = choice.data(Qt.ItemDataRole.UserRole) if choice else self.selected
        self.list.clear()
        system = QListWidgetItem('Tout le son Windows\nToutes les applications sur la sortie par défaut')
        system.setData(Qt.ItemDataRole.UserRole, {'mode': 'system', 'name': 'Tout le son Windows'})
        self.list.addItem(system)
        if wanted.get('mode') != 'application':
            self.list.setCurrentItem(system)
        if not supported():
            self.description.setText('Le choix d’une application nécessite Windows 11.\nLe mode « Tout le son Windows » reste disponible.')
            return
        try:
            apps = applications()
        except Exception as exc:
            self.description.setText('Actualisation impossible : ' + str(exc))
            return
        icons = QFileIconProvider()
        found = False
        for app in apps:
            state = 'Son en cours' if app['active'] else 'En pause / en attente de son'
            item = QListWidgetItem(icons.icon(QFileInfo(app['path'])), f"{app['name']}\n{state}")
            item.setToolTip(app['path'] + f"\nInstance : {app['pid']}")
            item.setData(Qt.ItemDataRole.UserRole, app)
            self.list.addItem(item)
            if wanted.get('mode') == 'application' and app['path'].casefold() == wanted.get('path', '').casefold():
                if not found or app['pid'] == wanted.get('pid'):
                    self.list.setCurrentItem(item)
                    found = True
        if wanted.get('mode') == 'application' and not found:
            missing = QListWidgetItem(f"{wanted.get('name', 'Application choisie')}\nFermée — attendre son retour")
            missing.setData(Qt.ItemDataRole.UserRole, wanted)
            self.list.addItem(missing)
            self.list.setCurrentItem(missing)
        elif self.list.currentItem() is None:
            self.list.setCurrentItem(system)

    def source(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None
