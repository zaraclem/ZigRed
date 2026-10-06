# État de qualification de ZigRed

Le workflow GitHub Actions compile le firmware pour ESP32-H2 DevKitM-1 4 Mo
avec Arduino-ESP32 3.3.2 et PN5180 Library 1.8.1. Consulter son résultat pour
la version exacte. Les fichiers USB et OTA sont publiés seulement après compilation.

Les contrôles locaux antérieurs couvrent la syntaxe Python et le convertisseur
simulé ; ils ne remplacent pas une installation HA ou un essai matériel.
Les nouveaux scénarios de tests dans `tests/` sont fournis sans annoncer leur réussite.

## Qualification matérielle encore nécessaire

1. Confirmer carte, module PN5180, tension, GPIO et mémoire de 4 Mo.
2. Flasher depuis le panneau HA, vérifier l’appairage Zigbee2MQTT et la version remontée.
3. Lire des tags ISO14443A de 4 ou 7 octets et ISO15693 de 8 octets.
4. Contrôler ajout, renommage, suppression et expiration de présence dans HA.
5. Publier une version supérieure, valider son installation OTA dans HA, suivre
   le transfert puis vérifier le redémarrage, la nouvelle version et les badges.
6. Qualifier les erreurs réseau et l’interruption d’alimentation pendant le transfert.

Aucune carte physique n’est connectée à cet environnement. Le transfert OTA,
le flash navigateur et le fonctionnement complet dans HA ne sont pas encore certifiés.
