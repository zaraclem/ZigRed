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
