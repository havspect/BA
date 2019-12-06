import xlwings as xw
import pandas as pd
from pandas.api.types import is_numeric_dtype
import numpy as np
import configparser


def autofit(wb):
    """autofit(wb)
    Funktion um die Datenblätter in die richtige Spaltenbreite zu übertragen!
    """
    for sheet in wb.sheets:
        if sheet.name not in ["Start", "Übersicht", "Daten"]:
            sheet.autofit()


def bekanntmachen(wb):
    """bekanntmachen(wb)
    Nimmt als Variable ein Workbook-Element und gibt als Returnwert ein Dict
    mit Pandas Datagrames und den in der Config-Datei hinterlegten Datein.

    wb: Workbook xlwings
    return Dict mit DataFrames
    """
    config = configparser.ConfigParser()
    config.read("config.ini")

    datenbase = dict()
    for key in config.sections():
        vals = dict(config.items(key))  # Umformatieren der Values in Dict
        if (
                vals.get("is_input") == "True"
                and vals.get("expand", False) != "table"
                and "range" in vals.keys()
        ):
            df = wb.sheets[
                vals.get("name_sht")
            ].range(vals.get("range")).options(
                pd.DataFrame,
                header=int(vals.get("header")),
                index=int(vals.get("index"))
            ).value
        elif vals.get("is_input") == "True":
            df = wb.sheets[
                vals.get("name_sht")
            ].range(vals.get("range")).options(
                pd.DataFrame,
                header=int(vals.get("header")),
                index=int(vals.get("index")),
                expand=vals.get("expand")
            ).value
        else:
            df = pd.DataFrame()  # leerer DF für Ergebnisse

        vals.update({"df": df})
        datenbase[key] = vals
    return datenbase


def extract_DataFrames(db):
    return {k: db[k].get("df") for k in db.keys()}


def print_DataFrame(name, df, db, wb):
    """print_DataFrame(name:String, df:DataFrame, db:Dict, wb:Workbook)
    Nimmt einen DataFrame und schreibt diesen in ein Tabellenblatt.

    name: Name der Tabelle wie in config.ini definiert
    df: DataFrame der geschrieben werden soll
    db: Dict mit den Dataframes und Tabellenblattnamen
    wb: Workbook Object
    """
    db = db[name]
    wb.sheets[db["name_sht"]].range(db["range"]).options(
        index=db["index"]
    ).value = df


def get_szenarios(db):
    return db["Technologiedaten"].get("df").columns.tolist()


def get_kategorien(db):
    return ["Transferzeit", "Wartezeit", "Fahrtzeit", "Length"] + list(
        dict.fromkeys(
            db["Technologiedaten"].get(
                "df").index.get_level_values("Kategorien")
        )
    )


class datenbasis():

    def __init__(self, df):
        self.df = df


def conv_db_in_format(dfs):
    ausgabe_dict = dict()
    for name, df in dfs.items():
        ausgabe_dict[name] = datenbasis(df)
    return ausgabe_dict


def main():
    wb = xw.Book.caller()
    db = bekanntmachen(wb)
    dfs = extract_DataFrames(db)
    db = conv_db_in_format(dfs)
    for name, df in db.items():
        df.df.to_hdf("data.h5", key=name)


if __name__ == "__main__":
    xw.Book("190910_Bewertungstool_v03.xlsm").set_mock_caller()
    main()
