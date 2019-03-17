import signal
import argparse
import sys
from logging.handlers import HTTPHandler
import logging
import click
from gpiozero import MCP3008
import time

##INIT
#Mise en place du logger
def initLogger():
	try:
		logger = logging.getLogger() #Logger console
		logger.setLevel(logging.DEBUG) #Définition du niveau de log par défaut, pour que les erreurs pendant l'init puissent être affichées
		
		logFormatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s', "%H:%M:%S") #Formatteur qui gère la mise en page des logs
		
		termLogger = logging.StreamHandler(sys.stdout)
		termLogger.setLevel(logging.DEBUG)
		termLogger.setFormatter(logFormatter)
		logger.addHandler(termLogger)
		#Mise en place du logger HTTP, qui va envoyer des logs sur un endpoint défini du site
		netLogger = HTTPHandler(host='blog.newe.space', url='/api/logger', method="POST", secure=True, credentials=('a','b',))
		netLogger.setLevel(logging.ERROR)
		logger.addHandler(netLogger)
		logger.debug('Initialisation du logger terminée')
		return logger

	except(Exception) as e:
		print(f"Une erreur est survenue lors de l'initialisation du logger: Traceback:\n{e}")
		sys.exit(0)

#Init du parser, qui gère les paramètres CLI
def initParser(l):

	@click.command()
	@click.option('-v', is_flag=True, help="Augmente la verbosité")
	def verboseFlag(v, l=l):
		if(v):
			click.echo(f"Niveau de logging défini sur verbose")
			l.setLevel(logging.DEBUG)
	
	@click.command()
	@click.option('-t', is_flag=True, help="Déclenche l'alarme pendant 10 secondes.")
	def testAlarm(t):
		if(t):
			print('dring')
	
	@click.command()
	@click.option('-s', is_flag=True, help="Ignore le préchauffage des composants")
	def testAlarm(t):
		return
			
#Initialisation des éléments de l'alarme via GPIO
def initGPIO(l):
	mq3 = MCP3008(0)
	cptPoussiere = MCP3008(1)

	l.info('Composants GPIO initialisés, 5 minutes de préchauffage vont maintenant démarrer...')
	a=0
	while a!=300:
		print(300-a)
		a+=1
		time.sleep(1)
	return mq3, cptPoussiere

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
	print("{0}\n\tDémarrage\n{0}".format('='*24))
	print("Initialisation du logger...")
	logger = initLogger()
	#logger.debug("Initialisation du parser...")
	#initParser(logger)
	logger.debug("Initialisation du GPIO...")
	mq3, cptPoussiere = initGPIO(logger)
	logger.info("Tous les modules ont étés initialisés!")
	while True:
		print("MQ3= {}, Poussiere = {}".format(mq3.value, cptPoussiere.value))
		time.sleep(5)