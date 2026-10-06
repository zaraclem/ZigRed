# ZigRed

<img src="custom_components/zigred/brand/icon.png" alt="Logo ZigRed : badge et ondes de lecture" width="160">

[![Ouvrir dans Home Assistant et ajouter à HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zaraclem&repository=ZigRed&category=integration)

Lecteur de présence de tags avec ESP32-H2, PN5180, Zigbee2MQTT et Home Assistant.
Le projet contient un firmware, un convertisseur Zigbee2MQTT et une intégration
Home Assistant. Il reste un **prototype logiciel** : le câblage, la radio, le flash USB, la lecture des tags
et l’OTA doivent être qualifiés sur du matériel réel. Le résultat de compilation
est visible dans GitHub Actions.

## Fonctions

- Lit les UID ISO 14443A de **4 ou 7 octets** et ISO 15693 de **8 octets**.
  La bibliothèque PN5180 choisie ne gère pas les UID ISO 14443A de 10 octets.
- Publie une lecture Zigbee environ toutes les 900 ms tant qu'un tag est détecté.
- Page **ZigRed** dans le menu HA : vue des lecteurs, noms, attributions UID/personne,
  ajout par scan ou saisie manuelle, modification et suppression propres à chaque lecteur.
- Désactivation temporaire d’une attribution pour 15 minutes, 1 heure, 24 heures,
  ou jusqu’à réactivation manuelle. La liste et les suspensions sont conservées localement.
- Trois entités de lecture par lecteur : **UID actif**, **Personne active**, **Lecture en cours**.
  L’entité **Firmware du lecteur** reste disponible pour les mises à jour OTA.
- Les lectures expirent environ 3 secondes après le dernier rapport radio frais.
  Les badges désactivés restent visibles dans la page mais sont ignorés par les entités.

Les UID identifient des tags mais ne prouvent pas l'identité d'une personne ;
ne pas les utiliser seuls pour une serrure ou une action de sécurité.

## Matériel à confirmer avant de brancher

- Carte **ESP32-H2** exacte, avec Zigbee. Une `ESP32-DevKitC-1` classique n'est
  pas une carte H2. Les broches ci-dessous supposent une `ESP32-H2-DevKitM-1`.
- Version du module PN5180, tension d'alimentation VCC prescrite par son
  fabricant et logique SPI **3,3 V** côté ESP32-H2.
- Masse commune, coordinateur Zigbee, Zigbee2MQTT, MQTT et Home Assistant.

| PN5180 | ESP32-H2-DevKitM-1 supposée |
| --- | --- |
| SCK | GPIO4 |
| MOSI | GPIO5 |
| MISO | GPIO0 |
| NSS / CS | GPIO1 |
| BUSY | GPIO10 |
| RST | GPIO11 |
| GND | GND |
| VCC | Selon **le module PN5180 exact** |
| IRQ | Non connecté |

Les `PIN_...` se règlent au début de `firmware/ZigRed_H2/ZigRed_H2.ino`. Confirmer les
GPIO disponibles sur **ta** carte avant de câbler. L'alimentation doit rester
présente : le firmware fonctionne comme routeur Zigbee.

## Activer la page ZigRed avant le premier lecteur

Après l’installation HACS et le redémarrage, ajouter l’intégration **ZigRed**
et valider **Activer l’espace ZigRed**. L’entrée **Espace ZigRed** conserve le
panneau du menu au démarrage, même sans appareil. Elle ne crée aucun lecteur
ni entité de lecture. La page est réservée aux comptes administrateurs.

Depuis cette page : préparer le flash USB, installer le convertisseur Zigbee2MQTT,
appairer le lecteur dans Zigbee2MQTT, puis cliquer sur **Ajouter un lecteur**
pour sélectionner l’appareil identifié. Ne pas supprimer l’entrée **Espace ZigRed**
si la page doit rester disponible sans lecteur.

## Flash USB depuis Home Assistant

Après installation de l’intégration, ouvre **ZigRed** dans la barre latérale de
Home Assistant. Branche le lecteur au **PC qui affiche la page**, avec un câble
USB de données. Dans Chrome ou Edge, ouvre HA en **HTTPS** (ou localhost), clique
**Préparer le firmware USB**, puis **Installer ZigRed** et sélectionne son port.

La version fournie cible exclusivement **ESP32-H2 DevKitM-1, 4 Mo**, avec le
câblage ci-dessus. Elle installe le firmware, les partitions et le client OTA.
Un effacement complet impose un nouvel appairage Zigbee. Une carte différente
nécessite une compilation adaptée. Le module Web Serial est fourni par
[ESP Web Tools](https://esphome.github.io/esp-web-tools/).

Le panneau télécharge une version GitHub publiée et vérifie son empreinte SHA-256
avant de proposer le flash. Le dépôt doit être public et sa première compilation
GitHub Actions réussie pour que les fichiers soient accessibles.

## Voyant RGB configurable (firmware 0.5.0)

Dans la page ZigRed, sélectionne un lecteur puis ouvre **Voyant LED · couleurs & comportements**. Chaque lecteur conserve ses propres réglages : couleur, activation et clignotement de chaque état, luminosité de 1 à 100 %, durée du résultat de 0,5 à 10 secondes. Désactive **En attente** pour laisser le lecteur éteint au repos, ou utilise **Tout éteindre** puis enregistre.

| État | Couleur par défaut |
|---|---|
| En attente | Bleu |
| Personne autorisée | Vert |
| Personne désactivée, temporairement ou manuellement | Rose |
| Badge absent de la liste du lecteur | Rouge |
| Vérification dans Home Assistant | Orange clignotant |
| Connexion Zigbee | Orange clignotant |
| Erreur du lecteur | Rouge clignotant |
| Mise à jour OTA | Violet clignotant |

L’autorisation provient de la liste de personnes propre au lecteur dans Home Assistant. Une lecture locale seule n’allume jamais le vert. Si HA ne répond pas, le lecteur indique une vérification en attente, puis revient au repos. Le résultat est associé à l’UID lu, les réponses pour un autre badge sont ignorées. Les noms restent dans HA.

Les réglages sont sauvegardés dans HA et dans la mémoire du lecteur. Le panneau distingue les réglages enregistrés de ceux confirmés par le lecteur. Pour activer la fonction, installer le firmware **0.5.0**, mettre l’intégration HACS à jour, installer le convertisseur fourni depuis le panneau, puis reconfigurer le lecteur dans Zigbee2MQTT si nécessaire.

Le voyant est sur GPIO8 de l’ESP32-H2 DevKitM-1. Les logs passent par la prise **USB directe**, à 115200 bauds. Le pilote PN5180 conserve les délais maximums BUSY/IRQ, les diagnostics et les nouvelles tentatives après échec. Les lectures réelles et les échanges LED restent à confirmer sur le matériel.

## Mise à jour sans câble : OTA Zigbee

Le lecteur n’a pas de Wi-Fi. Les mises à jour passent par **Zigbee2MQTT**, via son
coordinateur Zigbee. Après un premier flash USB et l’appairage, une entité
**Firmware du lecteur** apparaît sur la fiche Home Assistant du lecteur.

Quand une nouvelle version firmware est publiée, HA la recherche toutes les six
heures. Ouvre l’entité et valide **Installer**. Garde le lecteur alimenté et à
portée pendant le transfert et le redémarrage. L’ancien firmware sans client OTA
nécessite un premier flash USB. Le fonctionnement sur une carte physique reste
à qualifier, notamment le transfert complet et le retour après redémarrage.

L’intégration fournit l’URL OTA à Zigbee2MQTT au moment où tu cliques sur Installer.

## Publier une nouvelle version

1. Modifier le firmware, puis augmenter `version` dans `firmware/version.json`
   (par exemple `0.3.0` → `0.3.1`). Chaque nombre doit être entre 0 et 255.
2. Pousser sur `main`. GitHub Actions compile avec **Arduino-ESP32 3.3.2** et
   **PN5180 Library 1.8.1**, avec deux partitions de mise à jour de 1,25 Mo.
3. Après compilation, le workflow crée une release `vVERSION` contenant
   `zigred-h2-usb.bin`, `zigred-h2.ota` et `firmware.json`.
   Une version déjà publiée est conservée ; augmenter le
   numéro pour publier un nouveau firmware.
4. HA détecte la release et propose la mise à jour. Un simple changement de code
   sans nouveau numéro ne publie pas de nouvelle version firmware.

La mise à jour **HACS de l’intégration** et celle **du lecteur** sont distinctes.
Pour une version réservée à l’intégration, augmenter `version` dans
`custom_components/zigred/manifest.json` et pousser sur `main`. Si cette version
diffère de celle du firmware, le workflow publie une release avec les archives
du code uniquement. La recherche des mises à jour du lecteur continue à utiliser
la dernière release contenant `firmware.json`.

### Comprendre les assets d’une version

| Fichier | À quoi il sert |
| --- | --- |
| `zigred-h2-usb.bin` | Premier flash du lecteur branché en USB. |
| `zigred-h2.ota` | Mise à jour du lecteur sans câble, via Zigbee2MQTT. |
| `firmware.json` | Informations utilisées automatiquement par HA : version, carte ciblée, liens et empreintes de vérification. |
| `Source code (zip)` / `Source code (tar.gz)` | Archives du code ajoutées automatiquement par GitHub. Elles ne servent pas à flasher le lecteur. |

Depuis le panneau HA, aucun de ces fichiers n’est à choisir ou télécharger
manuellement. Les fichiers `web-manifest.json` et `ota-index.json` ont été retirés :
le panneau construit son manifeste USB et transmet directement l’URL OTA à Z2M.

### Compiler manuellement

Ouvrir `firmware/ZigRed_H2/ZigRed_H2.ino` dans Arduino IDE avec les versions de
bibliothèque ci-dessus, la carte ESP32-H2, `Zigbee ZCZR`, `Flash Size: 4MB` et
`Partition Scheme: Zigbee ZCZR`. La ligne de compilation utilisée est :

```sh
arduino-cli compile --fqbn 'esp32:esp32:esp32h2:ZigbeeMode=zczr,PartitionScheme=zigbee_zczr,FlashSize=4M,CDCOnBoot=cdc' --output-dir build firmware/ZigRed_H2
python scripts/package_firmware.py
```

## Installer Zigbee2MQTT

Dans le panneau **ZigRed** de Home Assistant, choisis ton lecteur puis clique
**Installer le convertisseur Zigbee2MQTT**. Le convertisseur inclus dans cette
version de l’intégration est envoyé à Zigbee2MQTT, qui l’enregistre et le charge
immédiatement. Le panneau affiche le résultat confirmé par Zigbee2MQTT.
Le bouton permet aussi de l’actualiser après une mise à jour HACS.

HA et Zigbee2MQTT doivent utiliser le même serveur MQTT. Si les convertisseurs
externes sont désactivés, activer une fois `advanced.enable_external_js: true`
dans Zigbee2MQTT et le redémarrer. Cette option n’est pas modifiée par le bouton.

### Installation manuelle alternative

Ajouter `zigbee2mqtt/zigred.js` comme convertisseur externe via
`Settings > Dev console > External converters` ou le répertoire
`external_converters` de ton installation. Autoriser l'appairage, démarrer le
lecteur et vérifier le modèle `ZigRed-H2`. Nommer l'appareil `zigred`
dans Zigbee2MQTT pour obtenir le sujet `zigbee2mqtt/zigred`.
Sur une installation récente où les convertisseurs externes sont désactivés,
activer `advanced.enable_external_js: true` dans Zigbee2MQTT et le redémarrer.

Une publication de lecture ressemble à ceci :

```json
{"uid":"A:04AABBCC","protocol":"ISO14443A","scan_seq":1}
```

`scan_seq` avance seulement lors d'un **nouveau rapport radio**. Zigbee2MQTT
peut republier un état MQTT ancien ; l'intégration HA exige une séquence
différente et ignore les messages MQTT conservés (`retain`). Une réponse à une
lecture d'attribut Zigbee n'est pas traitée comme une détection de tag.

## Installer l'intégration Home Assistant avec HACS

1. Cliquer sur le bouton bleu **Ouvrir dans Home Assistant** en haut de cette page.
2. Dans HACS, confirmer l'ajout de **ZigRed** comme intégration, puis télécharger
   ZigRed et redémarrer Home Assistant.
3. Activer MQTT dans Home Assistant et **appairer d’abord le lecteur dans
   Zigbee2MQTT**. Attendre la fin de son identification. Dans
   `Paramètres > Appareils et services`, ajouter **ZigRed**, indiquer le sujet de
   base Zigbee2MQTT (par défaut `zigbee2mqtt`), puis choisir le lecteur détecté.
   La liste affiche son nom, son modèle et son adresse Zigbee IEEE. Aucun appareil
   n’est créé par simple saisie d’un nom ou d’un sujet inventé.
   Home Assistant 2024.7 ou plus récent est requis.
4. Ouvrir **ZigRed** dans la barre latérale, puis cliquer sur le lecteur à configurer.
   Utiliser **Ajouter une personne** : saisir son nom et son UID, ou choisir
   **Lire un badge**, retirer tout badge déjà présent, puis présenter un nouveau badge
   à **ce lecteur**. L’attente s’annule après deux minutes.
5. La liste du lecteur permet de modifier le nom et l’UID, supprimer une attribution,
   désactiver temporairement une personne ou la réactiver.
6. Pour plusieurs lecteurs, appairer chacun dans Zigbee2MQTT, puis sélectionner
   chaque lecteur dans une entrée ZigRed distincte. Les sujets MQTT sont déduits des appareils (par exemple `zigbee2mqtt/entree`, `zigbee2mqtt/bureau`,
   `zigbee2mqtt/garage`). La page les affiche tous. L’adresse IEEE identifie chaque appareil même si son nom
   change dans Zigbee2MQTT. Un même UID peut être attribué
   différemment et désactivé séparément sur chacun.

Le dépôt GitHub s'appelle **ZigRed** et le domaine de l'intégration Home Assistant
est **zigred**. La prise en charge HACS installe l'intégration ; elle ne configure
pas le firmware ou le convertisseur Zigbee2MQTT, qui restent à installer selon
les sections précédentes.

### Nouveau logo dans Home Assistant

La version **0.3.2** inclut le nouveau logo dans `custom_components/zigred/brand/icon.png`.
Mettre à jour ZigRed dans HACS, redémarrer Home Assistant, puis actualiser la page
du navigateur (Ctrl+F5 si nécessaire). Le chargement des logos locaux des intégrations
nécessite **Home Assistant 2026.3 ou plus récent**. Cette mise à jour concerne
l’intégration et ne demande aucun flash du lecteur.

## Association et anciennes configurations manuelles

À partir de **0.4.1**, ZigRed lit l’inventaire `BASE/bridge/devices` de Zigbee2MQTT.
Il accepte seulement un modèle ZigRed-H2 ou THZReader-H2 dont l’identification
Zigbee est terminée. Il mémorise l’adresse IEEE et suit les changements de nom MQTT.
Un lecteur appairé n’est pas forcément allumé : l’inventaire valide son association,
pas une disponibilité radio instantanée.

Si une ancienne entrée saisie manuellement correspond à un vrai lecteur, elle est
associée automatiquement sans perdre ses personnes. Sinon, la page affiche
**À associer** et les entités restent indisponibles. Utiliser **Reconfigurer** dans
le menu de cette entrée sur la fiche de l’intégration, puis sélectionner le bon
lecteur. Les attributions sont conservées dans la même entrée.

## Entités et migration depuis 0.3.x

| Entité par lecteur | Pendant une lecture autorisée | Sans lecture autorisée |
| --- | --- | --- |
| **Personne active** | Nom enregistré, ou `Badge inconnu` | `Aucun` |
| **UID actif** | UID du badge | `Aucun` |
| **Lecture en cours** | `on` | `off` |

Une attribution désactivée ne produit pas de présence dans ces entités. La page
indique toutefois le badge détecté pour permettre sa gestion. Les trois entités
restent en lecture seule. Le lecteur conserve aussi son entité de mise à jour firmware.
Les états sont propres au sujet MQTT et à l’entrée de chaque lecteur.

**Migration 0.4.0 :** les noms et UID de chaque lecteur sont conservés automatiquement.
Les anciennes commandes de configuration, le capteur de liste, le dernier UID et les
capteurs de présence par personne sont retirés du registre des entités. Adapter les
automatisations qui les utilisaient. Les identifiants uniques des trois entités de
lecture existantes sont conservés ; leurs identifiants HA peuvent donc encore porter
les anciens noms. Pour les automatisations, lire les identifiants réels dans HA.

Les attributions sont stockées dans Home Assistant, pas dans le lecteur. Une suspension
avec durée se termine automatiquement même après un redémarrage. Suspendre une
personne ici s’applique uniquement à son attribution sur le lecteur sélectionné.

Si tu avais installé le prototype **THZReader**, sauvegarder ses noms avant de remplacer
l’intégration : le domaine `zigred` utilise un stockage distinct. Le convertisseur
reconnaît encore `THZReader-H2`, mais la migration des noms n’est pas automatique.

## Vérifications possibles sans matériel

Publier sur le sujet configuré un JSON avec un UID valide et `scan_seq` entier :

```json
{"uid":"V:E00401502A49F6D0","protocol":"ISO15693","scan_seq":1}
```

Répéter chaque seconde en augmentant `scan_seq`, puis arrêter. Le capteur **Lecture en cours** doit rester activé pendant les publications et s'éteindre environ trois
secondes après l'arrêt. Répéter avec `scan_seq` inchangé : le capteur ne doit pas rester activé. Ces essais vérifient la logique HA, pas le PN5180 ou Zigbee.

## Limites et suite matérielle

Le code PN5180 disponible lit les UID ISO 14443A de 4/7 octets et ISO 15693 de
8 octets ; son anticollision ISO 14443A à 10 octets n'est pas implémentée.
Une seule carte à la fois est prise en charge. Les deux protocoles alternent
sur la même antenne ; le temps de présence dépend de la qualité de lecture RF.

Il reste à confirmer par photos ou références exactes la carte H2 et le module
PN5180, consulter la compilation pour cette cible, vérifier un badge de chaque protocole, puis
tester l'ensemble avec Zigbee2MQTT et Home Assistant réels. Ne pas considérer
ce ZIP comme un firmware prêt à flasher sans cette vérification.

## Références

- [Carte ESP32-H2-DevKitM-1](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32h2/esp32-h2-devkitm-1/user_guide.html)
- [Zigbee Arduino ESP32](https://docs.espressif.com/projects/arduino-esp32/en/latest/zigbee/zigbee.html)
- [Bibliothèque PN5180](https://github.com/ATrappmann/PN5180-Library)
- [Convertisseurs externes Zigbee2MQTT](https://www.zigbee2mqtt.io/advanced/more/external_converters.html)


### Diagnostic série NFC

Les logs du firmware passent par la prise **USB directe** (USB CDC activé), tandis que la prise UART peut ne montrer que les messages ROM. Les étapes `initialize SPI`, `reset` et `read firmware EEPROM` permettent de localiser le blocage. Un message `PN5180 timeout` donne la phase exacte, le niveau BUSY attendu et celui observé. Cette correction supprime les attentes infinies ; elle ne garantit pas que le module répondra sur le matériel.

La compilation locale doit aussi appliquer `python3 scripts/patch_pn5180.py CHEMIN_BIBLIOTHEQUE_PN5180` sur une copie propre de la révision épinglée avant de compiler. Les modifications du pilote LGPL sont décrites dans ce script ; conserver la licence et les en-têtes originaux.

### Activation NFC et changements de protocole (0.4.7)

Les événements IRQ utilisés par le pilote sont activés explicitement. Avant chaque changement ISO14443A / ISO15693, le transceive est arrêté et le champ RF coupé, puis la configuration chargée et le champ réactivé. Les bits réservés de IRQ_CLEAR ne sont plus écrits. En cas de refus, les logs donnent SYSTEM_STATUS (paramètre, syntaxe, sémantique, TVDD) et RF_STATUS. Le firmware PN5180 interne reste inchangé ; le fonctionnement sur le lecteur réel doit être confirmé. Référence : [fiche technique NXP](https://www.nxp.com/docs/en/data-sheet/PN5180A0XX_C3_C4.pdf).

### Correction des erreurs IRQ persistantes (0.4.8)

Comparaison avec le pilote local de BambuNFCBridge : un événement de fin RF valide confirme la commande. La 0.4.7 pouvait rejeter une coupure RF achevée en présence d’une erreur sémantique antérieure. La 0.4.8 efface les événements avant chaque commande RF_ON/RF_OFF et vérifie d’abord son événement de fin. Les vrais refus et délais dépassés restent diagnostiqués. La pause entre lectures est de 110 ms. Le résultat doit être confirmé sur le lecteur réel.
