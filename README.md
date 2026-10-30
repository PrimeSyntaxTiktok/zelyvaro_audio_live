# ZELYVARO Audio Live

Visualiseur audio Windows vertical 9:16 pour TikTok Live Studio. Capture le son de la sortie Windows par défaut via WASAPI loopback (Spotify, navigateur, jeux).

## Installation
Téléchargez l'installateur depuis [Releases](https://github.com/PrimeSyntaxTiktok/zelyvaro_audio_live/releases) après publication d'une version. Le workflow GitHub Actions compile automatiquement sur Windows lors d'un tag `v*` et peut aussi être lancé depuis l'onglet Actions (workflow_dispatch, artefact téléchargeable).

## Fonctionnement
Ouvrez ZELYVARO Audio Live; la capture du périphérique Windows par défaut démarre automatiquement. Dans TikTok Live Studio, ajoutez une capture de la fenêtre du logiciel. Le format est vertical 9:16. Menu « Relancer capture audio » si vous changez de périphérique de sortie.

## Mise à jour
Dans le menu, « Vérifier les mises à jour » cherche la dernière version sur GitHub Releases de ce dépôt. Pour publier une version, augmentez VERSION dans app/main.py et AppVersion dans installer.iss, puis créez une release avec le tag correspondant (ex. v1.0.1). L'application propose de télécharger et lancer le nouvel installateur.

## Développement
Sur Windows avec Python 3.11 : `pip install -r requirements.txt` puis `python app/main.py`. Pour un exécutable, utilisez `build.ps1` puis Inno Setup 6 (installer.iss).

Le logiciel ne sauvegarde pas le son. Les exécutables générés sont non signés et peuvent déclencher SmartScreen. La capture est limitée au périphérique audio par défaut. Testez la capture WASAPI sur votre installation Windows.
