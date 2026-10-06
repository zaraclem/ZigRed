"""Reader LED settings and versioned, compact Zigbee wire format."""
import re
from copy import deepcopy

STATES = ('idle', 'authorized', 'denied', 'unknown', 'pending', 'pairing', 'error', 'ota')
DEFAULTS = {
    'brightness': 15, 'duration': 2000,
    'states': {name: {'enabled': True, 'color': color, 'blink': blink}
               for name, color, blink in zip(STATES,
                   ('#087ead', '#00ff00', '#ff1493', '#ff0000', '#ffb000', '#ffb000', '#ff0000', '#aa00ff'),
                   (False, False, False, False, True, True, True, True))},
}


def validate_settings(value):
    if not isinstance(value, dict) or set(value) != {'brightness', 'duration', 'states'}:
        raise ValueError('Réglages LED invalides.')
    if type(value['brightness']) is not int or not 1 <= value['brightness'] <= 100:
        raise ValueError('Luminosité attendue : 1 à 100 %.')
    if type(value['duration']) is not int or not 500 <= value['duration'] <= 10000:
        raise ValueError('Durée attendue : 500 à 10000 ms.')
    if not isinstance(value['states'], dict) or set(value['states']) != set(STATES):
        raise ValueError('États LED incomplets.')
    for state in value['states'].values():
        if (not isinstance(state, dict) or set(state) != {'enabled', 'color', 'blink'}
                or type(state['enabled']) is not bool or type(state['blink']) is not bool
                or not isinstance(state['color'], str)
                or not re.fullmatch(r'#[0-9a-fA-F]{6}', state['color'])):
            raise ValueError('Couleur ou comportement LED invalide.')
    return deepcopy(value)


def encode_settings(value):
    return '01' + f"{value['brightness']:02X}{value['duration']:04X}" + ''.join(
        f"{int(value['states'][state]['enabled'])}{int(value['states'][state]['blink'])}"
        + value['states'][state]['color'][1:].upper() for state in STATES)
