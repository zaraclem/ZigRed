# Diagnostic PN5180 sur ESP32-H2

Firmware temporaire pour ESP32-H2 4 Mo avec les GPIO habituels de ZigRed.
Utilise uniquement Arduino et SPI : aucune bibliothèque PN5180, aucun Zigbee,
aucune LED et aucun champ RF. Il ne lit donc pas les badges.

Il compare 100 kHz, 1 MHz et 7 MHz, avec deux modes de fin de réponse SPI,
et affiche les octets reçus ainsi que la stabilité de deux lectures EEPROM.
Une lecture stable est un indice de communication ; elle ne valide pas la lecture NFC.

Installation : ouvrir https://web.esphome.io dans Chrome ou Edge, connecter le
port du lecteur, choisir INSTALL puis sélectionner zigred-h2-diagnostic-usb.bin.
Le fichier contient le bootloader, les partitions et l'application temporaire.
Cette installation peut réinitialiser les données Zigbee du lecteur : prévoir
un nouvel appairage après remise du firmware ZigRed normal.

Ouvrir les logs à 115200 bauds, appuyer sur RESET et copier la sortie complète
jusqu'à DONE. Envoyer r pour répéter. La LED éteinte est normale.

Retour : réinstaller le firmware normal depuis la page ZigRed de Home Assistant.
Ce diagnostic n'est pas proposé en OTA ni comme version stable dans HA.
