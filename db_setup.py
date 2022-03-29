from dilution_db import DilutionDB
from configparser import ConfigParser

config = ConfigParser()
config.read("./config.cfg")
ddb = DilutionDB(config["dilution_db"]["connectionString"])