import signal
import argparse
import sys
from logging.handlers import HTTPHandler
import logging

##VARIABLES GLOBALES 
logger=None
logFormatter=None
parser=None
args=None

##INIT
#Mise en place du logger
def initLogger():
	try:
		logger = logging.getLogger() #Logger console
		logger.setlevel(logging.INFO) #Définition du niveau de log par défaut, pour que les erreurs pendant l'init puissent être affichées

		logFormatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s') #Formatteur qui gère la mise en page des logs
		logger.formatter(logFormatter)

		#Mise en place du logger HTTP, qui va envoyer des logs sur un endpoint défini du site
		netLogger = HTTPHandler(host='blog.newe.space', url='/api/logger', method="POST", secure=True, credentials=('a','b',))
		netLogger.setLevel(logging.ERROR)
		netLogger.formatter(logFormatter)

		logger.addHandler(netLogger)

		return True

	except(Exception) as e:
		print(f"Une erreur est survenue lors de l'initialisation du logger: Traceback:\n{e}")
		sys.exit(0)

#Init du parser, qui gère les paramètres CLI
def initParser():
	try:
		parser = argparse.ArgumentParser()
		parser.add_argument("--test", help="Déclenche l'alarme pendant 10 secondes.")
		parser.add_argument("--test-all", help="Déclenche l'alarme pendant 10 secondes, sur tous les systèmes.")
		parser.add_argument("-v", help="Augmente la verbosité")
		args = parser.parse_args()

	except(Exception) as e:
		logger.ERROR(f"Une erreur est survenue lors de l'initialisation du parser: Traceback:\n{e}")
		sys.exit(0)

#Initialisation des éléments de l'alarme via GPIO
def initGPIO():
	return False



#Création du gérant de signal, en cas de fermeture forcée
def signalHandler(sig, frame):
	print("Le programme enregistre les changements avant de s'arrêter, veuillez patienter.", end="")
	#Intégrer ici la fermeture douce de tous les services
	#Animation à intégrer avec le multithreading ↓↓↓
	#animation = "|/-\\"
	#idx=0
	#print(animation[idx % len(animation)], end="\r")
	sys.exit(0)

signal.signal(signal.SIGINT, signalHandler)

##FIN INIT

##COEUR DU PROGRAMME
if __name__ == "__main__":
	initLogger()
	initParser()
	if(args.v):
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)