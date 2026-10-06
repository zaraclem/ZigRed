# ZigRed 0.5.0 — Voyant configurable par lecteur

- Page LED par lecteur : couleurs, activation, clignotement, luminosité et durée du résultat.
- Vert pour autorisé, rose pour désactivé et rouge pour inconnu, avec couleurs modifiables.
- Repos désactivable et bouton pour éteindre tous les états.
- Verdict envoyé par HA au lecteur par Zigbee, associé à l’UID lu. Aucun faux vert sur une simple lecture locale.
- Réglages persistants dans HA et dans le lecteur, confirmation de synchronisation affichée.
- Conserve USB, OTA, appairage et diagnostics PN5180.

Installation : mettre l’intégration HACS à jour, installer le nouveau convertisseur Zigbee2MQTT depuis la page ZigRed, et flasher le firmware 0.5.0 sur le lecteur. Les anciens firmwares continuent de lire les badges mais ne prennent pas en charge les réglages LED. La compilation ne remplace pas une vérification sur le matériel.
