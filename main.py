# coding: utf-8
import os
import sys
from datetime import datetime
from time import sleep
from math import pi
import serial

import logging
from logging.handlers import HTTPHandler

from gpiozero import MCP3008

import requests

import json

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dbinteraction import dbexec

# INIT
# Mise en place du logger


def initLogger():
	try:
		print("Initialisation du logger...")
		logger = logging.getLogger()  # Logger console
		# Définition du niveau de log par défaut, pour que les erreurs pendant l'init puissent être affichées
		logger.setLevel(logging.DEBUG)

		# Formatteur qui gère la mise en page des logs
		logFormatter = logging.Formatter(
			'%(asctime)s :: %(levelname)s :: %(message)s', "%H:%M:%S")

		termLogger = logging.StreamHandler(sys.stdout)
		termLogger.setLevel(logging.INFO)
		termLogger.setFormatter(logFormatter)
		logger.addHandler(termLogger)
		# Mise en place du logger HTTP, qui va envoyer des logs sur un endpoint défini du site
		"""
		netLogger = HTTPHandler(host='blog.newe.space', url='/api/logger',
								method="POST", secure=True, credentials=('a', 'b',))
		netLogger.setLevel(logging.ERROR)
		logger.addHandler(netLogger)
		"""
		logging.getLogger("requests").setLevel(logging.DEBUG)
		logger.debug('Initialisation du logger terminée')
		return logger

	except(Exception) as e:
		print("Une erreur est survenue lors de l'initialisation du logger: Traceback:\n{}".format(e))
		sys.exit(0)

# Initialisation des éléments de l'alarme via GPIO


def initSensors(l):
	l.debug("Initialisation des composants...")
	cptPoussiere = MCP3008(0)
	ser = serial.Serial('/dev/ttyACM0', 9600, timeout=5)
	l.info('Composants GPIO initialisés, 5 minutes de préchauffage vont maintenant démarrer...')
	return cptPoussiere, ser

# FIN INIT


s = smtplib.SMTP_SSL('mail.newe.space', 465)


def sendMail(clientMail, args):
	try:
		msg = MIMEMultipart()
		msg['From'] = 'Alarme Incendie TSTI <adminproj@newe.space>'
		msg['To'] = clientMail
		msg['Subject'] = "ALERTE: Taux de gaz anormal"
		message = "Des valeurs anormales ont été détectées par votre dispositif d'alerte incendie.\n\
			Taux de particules fines: {} pcs/0.01f, {}/4\n\
			Taux de Monoxyde de Carbone: {}\n\
			Pollution de l'air: {}/4\n".format(args[0], args[1], args[2], args[3])

		msg.attach(MIMEText(message))
		s.login("adminproj@newe.space", os.environ['mailPass'])
		s.sendmail('adminproj@newe.space', clientMail, msg.as_string())
		s.quit()
	except(Exception) as e:
		print(e)


def sendDiscordAlert(vals, p):
	try:
		payload = {"embeds": [
			{
				"title": "Alarme déclenchée",
				"color": 16711684,
				"footer": {
					# "icon_url": "",
					"text": datetime.now().strftime("%d/%m %H:%M:%S")
				},
				"thumbnail": {
					"url": "https://newe.space/assets/images/siv.gif"
				},
				"fields": [
					{
						"name": "Taux de poussière",
								"value": "{}/??".format(round((1-p.value)*100, 2)),
						"inline": True
					},
					{
						"name": "Taux de gaz",
								"value": "{}/??".format(vals[0]),
						"inline": True
					},
					{
						"name": "Qualité de l'air",
								"value": "{}/??".format(vals[1]),
						"inline": True}
				]
			}
		]
		}
		headers = {'Content-Type': 'application/json'}
		response = requests.post(
			"https://canary.discordapp.com/api/webhooks/564025062324174868/uqjsPfNeC8bxT8nWT5D-6sTKSauyWkJWjgzxSdgKVmYqggTeAE6aH8VhqH6AooQV95j9", data=json.dumps(payload), headers=headers)
		return response

	except(Exception) as e:
		logger.error(e)

#Conversions des valeurs brutes du détecteur de poussière en valeurs exploitables
def pm25pcs2ugm3(pcs):
	density = 1.65 * pow(10, 12)
	r25 = 0.44 * pow(10, -6)
	vol25 = (4/3) * pi * pow(r25, 3)
	mass25 = density * vol25
	K = 3531.5

	return(pcs*K*mass25)


def pm25ugm32aqi(concentration_ugm3):
	pm25aqi = [
		{"clow": 0.0, "chigh": 12.0, "llow":  0, "lhigh": 50},
		{"clow": 12.1, "chigh":  35.4,  "llow": 51, "lhigh": 100},
		{"clow": 35.5, "chigh":  55.4, "llow": 101, "lhigh": 150},
		{"clow": 55.5, "chigh": 150.4, "llow": 151, "lhigh": 200},
		{"clow": 150.5, "chigh": 250.4, "llow": 201, "lhigh": 300},
		{"clow": 250.5, "chigh": 350.4, "llow": 301, "lhigh":  350},
		{"clow": 350.5, "chigh": 500.4, "llow": 401, "lhigh": 500}]
	for i in range(0, 8):
		if (concentration_ugm3 >= pm25aqi[i]["clow"] and concentration_ugm3 <= pm25aqi[i]["chigh"]):
			return ((pm25aqi[i]["lhigh"] - pm25aqi[i]["llow"]) / (pm25aqi[i]["chigh"] - pm25aqi[i]["clow"])) * (concentration_ugm3 - pm25aqi[i]["clow"]) + pm25aqi[i]["llow"]
		return 0


def conversions(v, c, q):
	air = None
	dust = None

	# POUSSIERE
	if(c >= 0 and c < 500):
		dust = 1
	elif(c >= 500 and c < 1500):
		dust = 2
	elif(c >= 1500 and c < 4000):
		dust = 3
	elif(c > 4000):
		dust = 4
	else:
		dust = 0

	# AIR
	_currentVoltage = 0
	_lastVoltage = _currentVoltage
	_currentVoltage = v
	if (_currentVoltage - _lastVoltage > 400 or _currentVoltage > 700):
		air = 4

	elif (_currentVoltage - _lastVoltage > 400 and _currentVoltage < 700):
		air = 3

	elif (_currentVoltage - _lastVoltage > 200 and _currentVoltage < 700):
		air = 2
	else:
 		air = 1

	#MQ3
	sensor_volt= q/1024*5.0
	RS_gas = (5.0-sensor_volt)/sensor_volt
	ratio = RS_gas/0.047339733973397344 #Valeur trouvée lors de la stabilisation du MQ3

	return air, dust, ratio


def warmq3(v): #Stabilisation du MQ3
	sensor_volt = 0
	RS_air=0 #  Get the value of RS via in a clear air
	R0=0  # Get the value of R0 via in Alcohol
	sensorValue=0

	for i in range(0,101):
		sensorValue += v
	sensorValue = sensorValue/100.0

	sensor_volt = sensorValue/1024*5.0
	RS_air = (5.0-sensor_volt)/sensor_volt
	R0 = RS_air/60.0

	print("R0 = {}".format(R0))
	#0.04522963285339522 >>valeur actuelle

def triggerAlarm(args, stop=False):
	if stop==True:
		return
	else:
		try:
			requests.post("http://127.0.0.1:5561/api/alarm", data={'status': 1})
		except requests.HTTPError:
			print('HTTP err')

		try:
			mailList = dbexec("SELECT mail from comptes where email = 1", mult=True, db="/home/pi/siteprojet/db/store.db")
			for i in mailList:
				sendMail(i, args)
		except:
			print('Mail error')
		
# COEUR DU PROGRAMME
if __name__ == "__main__":
	#Init des variables globales
	val = 0 #Déclenchement de l'alarme
	curv = 0

	print("{0}\n\tDémarrage\n{0}".format('='))

	#Séquence d'initialisation
	logger = initLogger()
	cptPoussiere, ser = initSensors(logger)

	logger.info("Tous les modules ont étés initialisés!")

	#Boucle principale
	while True:
		try:
			vals = ser.readline()[:-2].decode("utf-8").split(',')
		except serial.SerialExceptioon:
			print("Impossible de contacter l'Arduino")

		concentration = int(1.1*pow(cptPoussiere.value, 3)-3.8 *pow(cptPoussiere.value, 2)+520*cptPoussiere.value+0.62) #Calcul de la concentration de poussière en pcs/0.01f

		airQual, dustQual, mq3Qual = conversions(int(vals[1]), concentration, int(vals[0])) #Calcul du niveau de particules

		logger.info("MQ3: {} | Air: {} | Poussiere = {} pcs/0.01f | Alarme: {}/3".format(vals[0], vals[1], concentration, val))
		logger.warning(" {}, {}, {}".format(airQual, dustQual, mq3Qual))
		
		try:
			requests.post("http://127.0.0.1:5561/api/sensordata", data={
				'mq3': vals[0], 'cptPoussiere': concentration, 'PoussiereNote': dustQual, 'cptQualAir': vals[1], 'qualAirNote': airQual})
		except requests.HTTPError:
			print('Impossible de contacter la dashboard web.')

		if(dustQual>=3 or airQual>=3): #Si les valeurs des captuers dépassent les paliers données n fois de suite
			val += 1
		else:	#On vérifie que la valeur obtenue n'est pas un faux positif
			val = 0

		if(val >= 3):	#Checker de faux positif, ne se déclenche que si 3 valeurs dangeureuses ont étées détectées
			triggerAlarm(stop=False, args=[concentration, dustQual, mq3Qual, airQual])
		
		sleep(1) #Une seconde entre chaque boucle
