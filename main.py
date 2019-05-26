# coding: utf-8
import os
import sys
import asyncio
import subprocess
from datetime import datetime
from time import sleep
from dbinteraction import dbexec
import serial

import logging

import requests
import json

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl

loop = asyncio.get_event_loop()

def checkTest():
	r = requests.get('http://127.0.0.1:8080/api/test', timeout=5)
	rj = r.json()
	return rj['status']

class Alarme():
	def __init__(self):
		print("{0}\n\tDémarrage\n{0}".format('='*24))

		self.logger = self.initLogger()
		self.ser = self.initSensors()

		self.airQual = None #Note qual air x/4
		self.mq3Qual = None #note MQ3 x/4
		self.vals = [] #Array des valeurs de l'arduino
		self.temp = None #Valeur capteur température (°C)
		self.tempAlert = None #True si temp>40
		self.logger.info("Tous les modules ont étés initialisés!")

		self.val = 0 #Protection contre les faux-positifs
		self.curv = 0 #
		self.sent = False #True si les maisl ont étés envoyés
		self.triggered = False #True si l'alarme a été déclenchée

	def initLogger(): # Mise en place du logger
		try:
			print("Initialisation du logger...")
			logger = logging.getLogger()  # Logger console
			logger.setLevel(logging.DEBUG) # Définition du niveau de log par défaut, pour que les erreurs pendant l'init puissent être affichées

			# Formatteur qui gère la mise en page des logs
			logFormatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s', "%H:%M:%S")

			termLogger = logging.StreamHandler(sys.stdout) #Création du logger console
			termLogger.setLevel(logging.INFO)
			termLogger.setFormatter(logFormatter)
			logger.addHandler(termLogger)
			logging.getLogger("requests").setLevel(logging.DEBUG)
			logger.debug('Initialisation du logger terminée')
			return logger

		except(Exception) as e:
			print("Une erreur est survenue lors de l'initialisation du logger: Traceback:\n{}".format(e))
	
	def initSensors(self):
		self.logger.debug("Initialisation des composants...")
		ser = serial.Serial('/dev/ttyACM0', 9600, timeout=5)
		self.logger.info('Composants intialisés')
		return ser
	
	def getValues(self, test=False):
		if(test):
			self.airQual, self.mq3Qual, self.vals[
				0], self.vals[1] = 999, 999, 999, 999
		else:
			try:
				self.vals = self.ser.readline()[:-2].decode("utf-8").split(',')
			except serial.SerialException:
				self.logger.error("Impossible de contacter l'Arduino")

			self.airQual, self.mq3Qual = self.conversions(int(self.vals[1]), int(self.vals[0]))
			self.temp = float(self.vals[2])

			if(int(self.vals[3]) == 1):
				self.tempAlert = True
			else:
				self.tempAlert = False

	def checkExtAlarm(self):
		r = requests.get('http://127.0.0.1:8080/api/alarm')
		rj = r.json()
		print(rj)
		if(rj['status'] == 1 and rj['triggeredBy'] != 1):
			return True
		else:
			return False

	def conversions(self, v, q):
		air = None

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

		# MQ3
		sensor_volt = q/1024*5.0
		RS_gas = (5.0-sensor_volt)/sensor_volt
		ratio = RS_gas/0.047339733973397344 # Valeur trouvée lors de la stabilisation du MQ3
		return air, ratio

	def warmq3(self, v):  # Stabilisation du MQ3
		sensor_volt = 0
		RS_air = 0  # Get the value of RS via in a clear air
		R0 = 0  # Get the value of R0 via in Alcohol
		sensorValue = 0
		for i in range(0, 101):
			sensorValue += v
		sensorValue = sensorValue/100.0
		sensor_volt = sensorValue/1024*5.0
		RS_air = (5.0-sensor_volt)/sensor_volt
		R0 = RS_air/60.0
		print("R0 = {}".format(R0))
		# 0.04522963285339522 >>valeur actuelle

	def sendMail(self, clientMail, args):
		self.logger.debug('BEGIN mail call')
		if(self.sent != True):
			try:
				msg = MIMEMultipart()
				msg['From'] = 'Alarme Incendie TSTI <adminproj@newe.space>'
				msg['To'] = ", ".join(clientMail)
				msg['Subject'] = "ALERTE: Taux de gaz anormal"
				message = None
				if args:
					message = "Des valeurs anormales ont été détectées par votre dispositif d'alerte incendie.\n\
						Taux de Monoxyde de Carbone: {}\n\
						{}\n\
						Température: {}°C".format(args[0], args[1], args[2])
				else:
					message = "le module 2 s'est déclenché"

				msg.attach(MIMEText(message))
				with smtplib.SMTP_SSL('mail.newe.space', 465, context=ssl.create_default_context(), source_address=("0.0.0.0", 0)) as s:
					s.login("adminproj@newe.space", os.environ.get('mailPass'))
					s.sendmail('adminproj@newe.space',
							   clientMail, msg.as_string())
					self.logger.debug('Mails envoyés')
					s.quit()
				self.sent = True
			except(Exception) as e:
				print(e)

	def triggerAlarm(self, args, stop=False, ext=False):
		if not self.triggered or stop: #Empêchement des doublons
			try:
				data = None
				if stop:
					self.logger.debug('Alarme arretée')
					data = {'status': 0, 'trigTime': None, 'id': 1}
					loop.stop() #Arrêt de la loop
				else:
					self.logger.critical('ALARME DECLENCHEE')
					asyncio.ensure_future(subprocess.run(["aplay", "/home/pi/projet/alarm.wav"])) #Ajout de la lecture du son à la loop
					loop.run_forever() #Démarage de la loop
					try:
						a = []
						mailList = dbexec("SELECT lemail FROM comptes WHERE sendmail = 1",
										  mult=True, db="/home/pi/projet/db/store.db")
						for i in mailList:
							a.append(i[0])
							self.sendMail(a, args)
					except:
						self.logger.warning("Impossible d'envoyer les mails")

					data = {'status': 1, 'trigTime': str(datetime.now()), 'id': 1}
					self.triggered = True

				if not ext:
					try:
						requests.post(
							"http://127.0.0.1:8080/api/alarm", json=data)
					except requests.HTTPError:
						self.logger.error('HTTP err')

			except(Exception) as e:
				self.logger.error(e)


# COEUR DU PROGRAMME
if __name__ == "__main__":
	sent = None
	a = Alarme()
	while True:
		try:
			test = checkTest()
			a.getValues(test)
			# a.logger.warning("{}/4, {}/4, val {}/3".format(a.airQual, round(a.mq3Qual, 2), a.val))
			r = requests.post("http://127.0.0.1:8080/api/sensordata", json={"id": 1,"data": {
																				'mq3': a.vals[0], 'cptQualAir': a.vals[1], 'qualAirNote': a.airQual, 'temp': a.temp, 'tempAlert': a.tempAlert}})

			if(a.checkExtAlarm() == True): #Check si un autre module s'est déclenché
				a.logger.debug('Alarm EXT')
				a.triggerAlarm(stop=False, args=None, ext=True)

			else:
				if(a.airQual >= 3 or a.temp >= 27 or a.mq3Qual >= 1000):
					a.val += 1
				else:  # On vérifie que la valeur obtenue n'est pas un faux positif
					a.val = 0
					a.sent = False
					a.triggered = False
					a.triggerAlarm(args=None, stop=True)

				if(a.val == 3):  # Checker de faux positif, ne se déclenche que si 3 valeurs dangeureuses ont étées détectées
					a.logger.debug('alarm TRIGGER')
					a.triggerAlarm(stop=False, args=[
						a.mq3Qual, a.airQual, a.temp])

		except(requests.HTTPError, requests.ConnectionError):
			a.logger.error('Impossible de contacter la dashboard web.')

		except(TypeError, ValueError):
			a.logger.warning('Arduino booting...')

		except:
			a.logger.error('misc err')

		finally:
			sleep(1)  # Une seconde entre chaque boucle
