# ZELYVARO Audio Live

Application Windows 10 (1809+) / 11 x64, fond animé vertical pour TikTok Live Studio.
Projet initial repris depuis ZelyvaroAudioLive_Source.zip, avec six scènes animées originales.

## Six décors animés

- **Stellar Drift** : nébuleuse, planète, poussières orbitales et étoiles filantes.
- **Neon District** : ville cyberpunk, pluie en profondeur et reflets sur chaussée mouillée.
- **Ember Rise** : rivière de lave, fumée et braises ascendantes.
- **Northern Lights** : aurore boréale en mouvement, sommets et neige.
- **Abyssal Bloom** : méduses aux tentacules animés, faisceaux sous-marins et plancton lumineux.
- **Liquid Gold** : rubans de métal fluide, gouttes dorées et éclats.

Le son module les lumières, mouvements et particules. Les scènes continuent leur animation ambiante
dans le silence ; aucun faux spectre n'est généré. Le bouton Thèmes ouvre le sélecteur et les réglages.

## Installation et utilisation

Télécharger `ZelyvaroAudioLive-<version>-setup.exe` depuis les [Releases](https://github.com/PrimeSyntaxTiktok/zelyvaro_audio_live/releases).
Installation dans le profil utilisateur, désinstallation via Windows. Aucun Python nécessaire sur le PC cible.
Le binaire est non signé : Windows peut afficher un avertissement de réputation.

Cliquer sur la **source audio en haut de l’écran**, ou **Audio > Choisir l’application audio…**.
Choisir **Tout le son Windows**, ou une application avec une session de lecture (Spotify, Deezer, navigateur, jeu…).
Si elle n’apparaît pas, lancer un son dans cette application puis cliquer sur **Actualiser les applications**.
Le choix d’application utilise l’API Windows de capture par processus et inclut ses processus enfants,
pour prendre en charge les navigateurs et les applications Electron. Les autres applications sont exclues.
Pour un navigateur, le son des onglets de ce même navigateur est inclus.
Ce mode nécessite **Windows 11**, ou Windows build 20348 minimum. Sur les versions plus anciennes,
le mode **Tout le son Windows** reste disponible via WASAPI loopback (PyAudioWPatch).
La source choisie est mémorisée. Si l’application est fermée, la capture attend son retour et tente
de se reconnecter au même exécutable, sans basculer sur le son global. Aucun réglage du mélangeur Windows n’est changé.
Le microphone n'est jamais ouvert. Le son n'est ni enregistré sur disque ni envoyé sur Internet.
Après un changement de casque/sortie, utiliser **Relancer capture audio**.
Une capture impossible est signalée ; le silence ne déclenche pas de faux spectre musical.
Les flux protégés ou les applications utilisant une autre sortie/exclusive peuvent ne pas être capturés.

Ajouter la fenêtre du logiciel comme source de capture dans TikTok Live Studio.
**H** masque les contrôles et les menus, **F** bascule en plein écran.
Les préférences visuelles sont conservées dans le profil Qt de l'utilisateur.

## Mises à jour

Le dépôt est fixé à `PrimeSyntaxTiktok/zelyvaro_audio_live`. Aucun token GitHub n'est embarqué.
Recherche au démarrage et toutes les quatre heures, ainsi que via le menu.
Seules les versions stables plus récentes sont proposées. Le téléchargement et l'installation demandent l'accord de l'utilisateur.
Le nom exact, le dépôt HTTPS, la taille et le SHA-256 publié par GitHub sont vérifiés avant de lancer l'installateur.
En cas d'erreur ou de corruption, aucun installateur n'est lancé.
Les téléchargements sont préparés dans un dossier unique sous `%LOCALAPPDATA%/ZelyvaroAudioLive/updates`.
L'installateur garde le même AppId, réutilise le dossier existant, ferme l'application et la relance après mise à jour.
Les préférences du profil utilisateur sont conservées.

## Compilation et futures versions

Python 3.12 x64, outils de compilation MSVC C++ avec SDK Windows 20348+ et Inno Setup 6.
Dépendances épinglées dans `requirements.txt`. Le build compile aussi le pont natif de capture par application.

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
./build.ps1
& 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe' installer.iss
```

Le workflow Windows installe les dépendances, lance les tests, compile avec PyInstaller,
teste le rendu WebEngine et le pont JavaScript dans l'EXE, puis construit l'installateur Inno Setup.
Il conserve les artefacts et publie une Release uniquement si cette version n'existe pas déjà.
Pour publier une nouvelle version, augmenter `VERSION` dans `app/version.py` puis pousser sur `main`.
Le build transmet cette version à Inno Setup et aux métadonnées Windows.
Un tag `vX.Y.Z` doit correspondre à la version du code.

## Vérification réelle du son (PC avec sortie audio)

```powershell
& 'dist/ZELYVARO Audio Live/ZELYVARO Audio Live.exe' --self-test resultat.json --require-audio --play-test-tone
```

Ce mode joue volontairement une courte tonalité de 1 kHz, mesure les échantillons capturés,
vérifie leur arrivée dans le rendu, prend une capture PNG et produit un rapport JSON.
Le workflow utilise un test de rendu sans imposer de matériel audio au runner GitHub.
Le test matériel optionnel `tests/integration_application_capture.py` joue deux tonalités depuis deux
programmes distincts, capture uniquement le premier (y compris son processus enfant), puis vérifie
l’exclusion du second, la pause et la reprise. Compiler le lecteur de test avec
`./tools/build-native.ps1 -BuildTestPlayer`, puis exécuter le script en lui passant un chemin de rapport JSON.
Le pont natif suit les API documentées par [Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/audioclientactivationparams/ns-audioclientactivationparams-audioclient_process_loopback_params).
Les dépendances Qt/PySide6, NumPy, PyAudioWPatch et packaging conservent leurs licences respectives, jointes à l'application.
