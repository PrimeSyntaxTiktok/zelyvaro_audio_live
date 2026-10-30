# ZELYVARO Audio Live 1.4.0

Visualiseurs musicaux plein écran pour Windows x64 et TikTok Live Studio / OBS.
La forme des effets vient du son capturé : 128 bandes logarithmiques, forme d’onde réelle, graves, médiums, aigus et détection d’impacts. Aucun faux spectre n’est généré en fonctionnement normal.

## Studio organisé

Quatre onglets : **Thèmes** (ambiances, compositions, fond), **Animation** (effets, particules, palette et sauvegarde), **Habillage** (pseudo, morceau, logo et placement), **Diffusion** (source audio, liens et performance). Les réglages précis sont repliables.

## Six thèmes et compositions personnelles

- **ECLIPSE** : couronnes de fréquences, impulsions et étoiles.
- **PRISM** : spectre miroir et étincelles électriques.
- **SHOCKWAVE** : rayons et impacts radiaux, braises.
- **FLUX** : nappes de formes d’onde et cristaux.
- **VORTEX** : tunnel de fréquences, bulles et orbes.
- **CHROMA** : cascade d’historique spectral, confettis et traînées.

Dans **Studio**, combiner plusieurs des six effets et des huit types de particules, choisir les couleurs puis enregistrer sa composition. Jusqu’à 64 compositions ; enregistrer sous le même nom remplace la composition. Régler sensibilité, mouvement, densité et 30/60 images par seconde selon le GPU. La source de diffusion utilise par défaut un rendu 4K UHD de 8 294 400 pixels. Le choix Full HD réduit la charge GPU si nécessaire ; la fluidité dépend des effets, de leur combinaison et du matériel. Les halos utilisent des textures réutilisées pour éviter de recalculer leurs dégradés à chaque image. Sans son, les particules tombent, s’effacent et disparaissent. Le bouton de test sans musique active une simulation explicitement identifiée.

Importer une image de fond PNG, JPEG, WebP ou BMP. L’image est copiée dans le profil du logiciel et reste disponible si le fichier d’origine est déplacé. Les images importées conservent jusqu’à 4096 pixels sur leur plus grand côté, notamment les fonds 2160 × 3840 et 3840 × 2160. Réimporter le fichier original si une ancienne version avait réduit le fond. Régler son assombrissement dans Studio.

## Installation et source audio

Prendre `ZelyvaroAudioLive-<version>-setup.exe` dans les [Releases](https://github.com/PrimeSyntaxTiktok/zelyvaro_audio_live/releases). Installation par utilisateur, sans Python sur le PC cible. Le binaire n’est pas signé.

Cliquer sur la source en haut de l’écran ou **Audio > Choisir l’application audio…**. Choisir tout le son Windows, ou une application ayant une session de lecture. Si elle manque, lui faire jouer un son puis actualiser la liste.

La capture par application nécessite Windows 11 / build 20348 minimum. Elle comprend les processus enfants de l’application, donc les onglets d’un même navigateur. Les autres applications sont exclues. Sur Windows 10 1809+, le son global reste disponible via WASAPI loopback. Le choix est mémorisé et la capture attend/retrouve l’application après son redémarrage, sans basculer automatiquement sur le son global. Aucun microphone n’est ouvert et aucun réglage du mélangeur Windows n’est changé. Après un changement de sortie audio, relancer la capture depuis le menu Audio. Les flux protégés ou les sorties exclusives peuvent être indisponibles.

## Pseudo, morceau et logo

Dans **Studio > Pseudo, morceau et logo**, choisir le bloc puis **Déplacer / redimensionner**. Glisser le bloc et tirer son angle inférieur droit. Les champs de position et de dimensions permettent un placement précis. Cocher **Verrouiller le placement** pour bloquer les déplacements et la taille. Chaque disposition est enregistrée et répercutée dans la diffusion. Les textes disposent de polices, gras, italique et couleur indépendants.

Le morceau est affiché en gras sur une seule ligne **Artiste — Titre**, avec une icône de musique vectorielle transparente à gauche. Le bloc reste déplaçable et verrouillable. Un vrai pictogramme musical vectoriel est affiché à gauche. Si le titre dépasse, il défile de droite à gauche à vitesse modérée, après une pause de 1,6 seconde. La vitesse suit la taille de police ; le défilement conserve la taille choisie et ne redémarre pas à chaque actualisation des métadonnées. Les titres courts restent fixes.

Windows fournit automatiquement artiste et titre pour les lecteurs qui publient leurs métadonnées de session multimédia (GSMTC). En mode application, seules les sessions correspondantes sont retenues. Certains lecteurs ne publient rien : utiliser la saisie manuelle ou les champs de remplacement. Il ne s’agit pas d’une reconnaissance musicale universelle.

Importer un logo du PC ou un lien HTTP(S) direct vers une image, utiliser le logo ZELYVARO ou retirer le logo. Les PNG conservent leur transparence. Le logo original fourni est inclus sans modification dans l’application ; son icône ICO multi-tailles sert à l’EXE, à l’installateur, aux raccourcis, à la barre des tâches et à la zone de notification.

## Diffuser en arrière-plan

Utiliser **Diffusion > Copier le lien de diffusion**, puis ajouter ce lien comme source **Lien / Navigateur** dans TikTok Live Studio ou OBS. Le dialogue propose **Portrait 9:16 (2160 × 3840 en 4K)** ou **Paysage 16:9 (3840 × 2160 en 4K)** et mémorise le dernier choix. Le lien remplit toute la surface de la source navigateur, sans cadre noir ni mise à l’échelle interne du visuel. Régler la largeur et la hauteur de la source dans TikTok Studio / OBS aux dimensions indiquées pour remplir le cadre ; une page ne peut pas modifier automatiquement les propriétés de la source de ces logiciels. Dans TikTok, activer la résolution personnalisée de la source Lien et saisir les dimensions choisies, puis ajuster le cadre à la scène. La taille d’un cadre déjà placé dans TikTok ne peut pas être modifiée par la page web. Dans OBS, utiliser ensuite Transformer > Ajuster à l’écran. Dans TikTok, ajuster/agrandir la source pour couvrir la scène : changer sa résolution ne réinitialise pas une transformation de scène déjà réduite. Une source laissée à 800 × 600 remplit aussi sa surface, mais reste capturée à 800 × 600 par le navigateur hôte, même si le moteur calcule en 4K. Diffusion affiche la résolution réellement reçue par chaque source et indique la correction nécessaire. Actualiser une ancienne source après la mise à jour. Le mode Full HD propose 1080 × 1920 ou 1920 × 1080. Changer de qualité ne change jamais les liens personnels. La résolution de sortie finale du live dépend aussi du logiciel de streaming. Deux liens de formats différents peuvent être utilisés simultanément. Si la version de TikTok Studio ne propose pas cette source, l’ouvrir dans une fenêtre de navigateur qui reste affichée et capturer cette fenêtre, ou utiliser OBS.

Le serveur reste local à 127.0.0.1, avec clé privée conservée dans le profil. La source navigateur effectue son propre rendu : elle continue quand les commandes de ZELYVARO sont réduites, cachées ou recouvertes par un jeu. La capture d’une fenêtre Windows réduite dépend du logiciel de streaming ; utiliser la source navigateur pour ce besoin. Le logiciel doit rester en fonctionnement. Une seule instance normale est autorisée par utilisateur, y compris depuis deux dossiers différents. Un second lancement restaure la fenêtre existante, même si elle est rangée en zone de notification. Fermer par la croix le range dans la zone de notification (ou le réduit si cette zone est indisponible) ; **Quitter** arrête le logiciel et la source. Chaque profil Windows conserve son identifiant personnel et son port local : ses deux liens portrait/paysage restent identiques après redémarrage, réinstallation et mise à jour tant que le profil est conservé. Deux profils ont des identifiants différents. Si le port enregistré est occupé, le logiciel signale le conflit et garde ses liens au lieu de changer de port. Conserver `%LOCALAPPDATA%/ZelyvaroAudioLive`, notamment `live-source-key.txt` et `stream-port.json`, pour garder cette identité. Le nom du processus reste `ZELYVARO Audio Live.exe`, sans numéro de version.

Le live ne montre ni nom du thème ni contrôles. Dans la fenêtre ZELYVARO active, **Échap** quitte le mode live et ouvre la configuration, **H** bascule les contrôles, **F** bascule le plein écran. Échap n’est pas un raccourci global interceptant les touches de vos jeux. Double-cliquer sur l’icône de notification restaure la fenêtre.

## Mises à jour GitHub

Le dépôt est fixé à `PrimeSyntaxTiktok/zelyvaro_audio_live`, sans token embarqué. Recherche automatique au démarrage puis toutes les quatre heures, et à la demande dans le menu. Seules les versions stables plus récentes sont proposées. Le téléchargement et l’installation demandent l’accord de l’utilisateur. Le dépôt HTTPS, le nom exact, la taille et le SHA-256 publié sont vérifiés avant de lancer l’installateur. Un échec annule l’installation. L’AppId et le dossier d’installation restent stables ; le profil visuel et les images sont conservés lors d’une mise à jour.

Les préférences, images et clé de diffusion sont dans `%LOCALAPPDATA%/ZelyvaroAudioLive`. Le son analysé n’est pas enregistré ni envoyé sur Internet. Seuls la recherche de mises à jour et un import explicite de logo par lien accèdent au réseau.

## Compiler et vérifier

Python 3.12 x64, MSVC C++20 avec SDK Windows 20348+ et Inno Setup 6. Dépendances épinglées dans `requirements.txt`.

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
./build.ps1
& 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe' installer.iss
```

Le workflow Windows teste le code, compile le pont natif, fige l’application, vérifie le rendu dans l’EXE puis construit l’installateur et le ZIP portable avec SHA-256. Il publie une Release stable pour une nouvelle version poussée sur main. Augmenter `VERSION` dans `app/version.py` ; un tag `vX.Y.Z` doit correspondre à cette version. Une version déjà publiée n’est pas remplacée.

Le diagnostic `--self-test rapport.json --gallery` contrôle les six rendus et leur différence entre silence et signal au même instant. Le runner n’a pas besoin de sortie audio. Sur un PC disposant d’une sortie, `--require-audio --play-test-tone` vérifie une tonalité de 1 kHz ; arrêter les autres sons pour ce test. `--studio-test` ajoute une source navigateur indépendante et vérifie qu’elle continue après réduction puis masquage des commandes. `--test-profile chemin` isole les préférences d’un diagnostic et nécessite `--self-test`.

Le test matériel `tests/integration_application_capture.py` vérifie l’isolation de deux applications, les processus enfants, la pause et la reprise ; compiler le lecteur par `./tools/build-native.ps1 -BuildTestPlayer`.

Le pont natif suit les API de capture par processus et de sessions multimédia de Microsoft. Les licences Qt/PySide6, NumPy, PyAudioWPatch, packaging et Heroicons (MIT, Tailwind Labs) sont jointes à l’application.
