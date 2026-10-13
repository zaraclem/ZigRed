# 0.5.3

Nouveau transport PN5180 ZigRed par GPIO : SPI mode 0 MSB-first généré directement, sans contrôleur SPI matériel Arduino. Les protections BUSY/IRQ et les protocoles ISO14443A/ISO15693 existants sont conservés. Le diagnostic 2 utilise le même transport GPIO sans Zigbee/RF/LED.

Ce changement vise à isoler la panne SPI persistante. Une compilation réussie ne confirme pas son efficacité sur le montage physique. Les UID, réglages LED et commandes OTA restent compatibles. Source du transport : drivers/zigred_pn5180/ZigRedPNTransport.h. Les routines de protocole amont restent sous LGPL-2.1-or-later.

# 0.5.2

Patch PN5180 basé sur le pilote Filament Reader : SPI 7 MHz et interrogation BUSY toutes les 50 microsecondes. Les délais maximaux et la récupération après erreur restent actifs. Le log indique désormais la commande SPI et son premier paramètre en cas de blocage.

Mise à jour du firmware nécessaire. La compilation ne confirme pas la résolution sur le matériel. Comparer avec le deuxième PN5180 et des fils courts. Flash USB sans effacement complet pour conserver l’appairage Zigbee.

# 0.5.1

Corrige les commandes LED apr�s une mise � jour du convertisseur Zigbee2MQTT : les attributs sont adress�s par num�ro pour �viter une ancienne d�finition en m�moire. Aucun nouveau flash firmware requis si le lecteur est d�j� en 0.5.0.

# ZigRed 0.5.0 — Voyant configurable par lecteur

- Page LED par lecteur : couleurs, activation, clignotement, luminosité et durée du résultat.
- Vert pour autorisé, rose pour désactivé et rouge pour inconnu, avec couleurs modifiables.
- Repos désactivable et bouton pour éteindre tous les états.
- Verdict envoyé par HA au lecteur par Zigbee, associé à l’UID lu. Aucun faux vert sur une simple lecture locale.
- Réglages persistants dans HA et dans le lecteur, confirmation de synchronisation affichée.
- Conserve USB, OTA, appairage et diagnostics PN5180.

Installation : mettre l’intégration HACS à jour, installer le nouveau convertisseur Zigbee2MQTT depuis la page ZigRed, et flasher le firmware 0.5.0 sur le lecteur. Les anciens firmwares continuent de lire les badges mais ne prennent pas en charge les réglages LED. La compilation ne remplace pas une vérification sur le matériel.
