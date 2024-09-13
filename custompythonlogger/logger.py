
from pathlib import Path
import json
import logging
import atexit

def setup_logging(config: None):
    """ :config: au format json """
    
    if not config:
        # si aucun fichier config n'est précisé, 
        # utiliser le fichier dans le dossier config
        config = Path(__file__).resolve().parent / 'config' / 'logging.json'
    
    with open(config, 'r') as f_in:
        config = json.load(f_in)
        
    logging.config.dictConfig(config)

    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)
