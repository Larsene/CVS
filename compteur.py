#!/usr/bin/python3.6
# -*-coding:UTF-8-*#

#----------------------------------------------------------------------
#  (c) David ROUBLOT, 2019
#----------------------------------------------------------------------

#----------------------------------------------------------------------
#IMPORTING
#----------------------------------------------------------------------
import requests
from flask import Flask, request, redirect, url_for, render_template
from waitress import serve
import configparser
from time import sleep

from datetime import datetime
import babel
from babel.dates import format_date, format_datetime, format_time

import threading

#  FLASK CONFIG
WEBSITE_ADDRESS = 'http://stalagtic-dev.ovh/cvs'

# Flask env
app = Flask(__name__)
app.debug= True
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
app.config.from_object(__name__)
app.config['WEBSITE_ADDRESS'] =  WEBSITE_ADDRESS
app.secret_key = ''

#----------------------------------------------------------------------
#  GLOBALS
#----------------------------------------------------------------------
#  we have to load this from config file, but ...

Sites = [{"ID" : 773508,
            "Name" : "CVS Marie Thal-Marmoutier",
            "API": ""
            },
            {"ID" : 858573,
            "Name" : "École du Bouc d’Or",
            "API": ""
            },
            {"ID" : 938645,
            "Name" : "Ecole de Dossenheim",
            "API": ""
            },
            {"ID" : 989673,
            "Name" : "Club House Saverne",
            "API": ""
            }
            ]

Update = format_datetime(datetime.now(), "d MMMM YYYY 'à' H'h'mm", locale='fr')

#----------------------------------------------------------------------
#  GETTING DATAS EVERY 15MINS
#----------------------------------------------------------------------
# simple function started as thread

semaphore_RefreshData = threading.Event()
def RefreshData():
    global Update, Sites
    error = False

    while not semaphore_RefreshData.isSet():

        for site in Sites:
            # requesting total prod
            r = requests.get(f"https://monitoringapi.solaredge.com/site/"
                             f"{site['ID']}/overview?api_key={site['API']}")
            if r.status_code == 200:
                JSONResult = r.json()
                site["lifetimeproduction"] = round(int(JSONResult["overview"]["lifeTimeData"]["energy"]) / 1000, 2)
            else:
                error = True

            # requesting additional envBenefits
            r = requests.get(f"https://monitoringapi.solaredge.com/site/"
                             f"{site['ID']}/envBenefits?systemUnits=Metrics&api_key={site['API']}")
            if r.status_code == 200:
                JSONResult = r.json()
                site["trees"] = round(JSONResult["envBenefits"]["treesPlanted"], 2)
                site["lightbulbs"] = round(JSONResult["envBenefits"]["lightBulbs"], 2)
                site["CO2"] = round(JSONResult["envBenefits"]["gasEmissionSaved"]["co2"], 2)
            else:
                error = True

        if not error is True:
            Update = format_datetime(datetime.now(), "d MMMM YYYY 'à' H'h'mm", locale='fr')

        sleep(900)

TaskerThread = threading.Thread(name="RefreshData", target=RefreshData)
TaskerThread.start()

#----------------------------------------------------------------------
# FLASK ROUTES                                                        #
#----------------------------------------------------------------------

@app.route('/')
@app.route('/index', methods=['GET','POST'])
def index():
    # 1 calculate the values to display
    Sites_Prod = '{:.2f}'.format(sum(item['lifetimeproduction'] for item in Sites))
    Sites_CO2 = '{:.2f}'.format(sum(item['CO2'] for item in Sites))
    Sites_Trees = '{:.1f}'.format(sum(item['trees'] for item in Sites))
    Sites_Bulbs = '{:.2f}'.format(sum(item['lightbulbs'] for item in Sites))
    Home_Use =  '{:.1f}'.format(float(Sites_Prod) / 2700)
    Car_Power = '{:.1f}'.format(float(Sites_Prod) / 18 * 100)
    Car_Planet = '{:.2f}'.format((float(Sites_Prod) / 20.3 * 100) / 40075)
    #  we also send the Sites dic to Flask

    return render_template('index.html',
                           Sites_Prod = Sites_Prod,
                           Sites_CO2 = Sites_CO2,
                           Sites_Trees = Sites_Trees,
                           Sites_Bulbs = Sites_Bulbs,
                           Home_Use = Home_Use,
                           Car_Power = Car_Power,
                           Car_Planet = Car_Planet,
                           Update = Update,
                           Sites = Sites)


#----------------------------------------------------------------------
# STARTING                                                            #
#----------------------------------------------------------------------

if __name__ == "__main__":
    print("starting ... Compteur Centrales Villageoises")
    import os
    if 'WINGDB_ACTIVE' in os.environ:
        app.debug = False
        app.run(host="0.0.0.0", port=5000)
    else:
        serve(app,  trusted_proxy = True, host='0.0.0.0', port='5005')