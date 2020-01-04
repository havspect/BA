import pandas as pd
import configparser

path = "../data/data.h5"

config = configparser.ConfigParser()
config.read("config.ini")

def loda_hdf(path):
    dfs = dict()
    for name in config.sections():
        dfs[name] = pd.read_hdf(path, key=name)
    return dfs


class datenbank():

    path = "../data/data.h5"
    config = configparser.ConfigParser()
    config.read("config.ini")

    def __init__(self):
        self.dfs = loda_hdf(path)
        self.cities = self.dfs["Staedte"]
        self.tech_data = self.dfs["Technologiedaten"]
        self.improve_data = self.dfs["Verbesserungsfaktoren"]
        self.rf_pv_basis = self.dfs["rf_pv_Basis"]
        self.rf_pv_pod = self.dfs["rf_pv_Pod"]
        self.rf_gv_basis = self.dfs["rf_gv_Basis"]
        self.rf_gv_pod = self.dfs["rf_gv_Pod"]
        self.rf_pv_routes = self.dfs["rf_pv_Strecken"].rename(columns=str.lower).drop('strecken_typ', axis=1)
        self.rf_gv_routes = self.dfs["rf_gv_Strecken"].rename(columns=str.lower).drop('strecken_typ', axis=1)

    
    def loda_hdf(self, path):
        dfs = dict()
        for name in config.sections():
            dfs[name] = pd.read_hdf(path, key=name)
        return dfs

    
    def save(self):
        pass



if __name__ == "__main__":
    db = datenbank()
    print(db.cities)