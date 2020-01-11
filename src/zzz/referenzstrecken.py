import numpy as np
import pandas as pd
import xlwings
from pandas.api.types import is_numeric_dtype
import subprocess
import os

from datenbasis_funktionen import *

oev_list = ["Bus", "Tram", "U-Bahn", "Zug-Nahverkehr", "Zug-Fernverkehr"]

per_trip_costs = ["Bus", "Tram", "U-Bahn", "Flugzeug"]


def build_cities(row, df, df_strecken, df_staedte):
    """build_cities(row)
    Hinzufügen der Stadttypen zu der Übersichtstabelle Verbindungen!

    row: pd.row
    """
    if row[("Allgemein", "Name_Verbindung")] in df_strecken.index.tolist():
        stadt_start = df_strecken.loc[row[(
            "Allgemein", "Name_Verbindung")], "Stadt_Start"]
        stadt_start_typ = df_staedte["Stadt_Typ"].loc[
            df_staedte.loc[:, "Stadt_Name"] == stadt_start
            ].values[0]
        stadt_ende = df_strecken.loc[row[(
            "Allgemein", "Name_Verbindung")], "Stadt_Ende"]
        stadt_ende_typ = df_staedte["Stadt_Typ"].loc[
            df_staedte.loc[:, "Stadt_Name"] == stadt_ende
            ].values[0]
        if stadt_start_typ == stadt_ende_typ:
            row["Stadttypen"] = stadt_start_typ
        else:
            row["Stadttypen"] = stadt_start_typ + " - " + stadt_ende_typ
    else:
        row["Stadttypen"] = np.nan

    return row



def anteil_row_bestimmen(stadttyp, row, col, df_bev, mult):
    if len(stadttyp) > 1:
        row[col] *= (df_bev.loc[col[0], stadttyp[0]] +
                     df_bev.loc[col[0], stadttyp[1]])
        row[col] /= mult
    else:
        row[col] *= df_bev.loc[col[0], stadttyp[0]]
        row[col] /= mult
    return row


def f3(row, df, df_bev, name):
    """f3(row, df, df_bev)

    """
    stadttyp = row["Stadttypen"].values[0]
    if " - " in stadttyp:
        stadttyp = stadttyp.split(" - ")
    else:
        stadttyp = [stadttyp]

    for col in df.columns.tolist():
        # Normalfall
        if is_number(row[col]) and col[0] != "Allgemein" and name[0] == "UK":
            row = anteil_row_bestimmen(stadttyp, row, col, df_bev, 1)
        # Da doppelte Anzahl an Strecken in UL -> Faktor 2
        elif is_number(row[col]) and name[0] == "UL" and col[0] != "Allgemein":
            row = anteil_row_bestimmen(stadttyp, row, col, df_bev, 2)
        # Da 2,5 fache Anzahl an Strecken in I -> Faktor 2,5
        elif is_number(row[col]) and name[0] == "I" and col[0] != "Allgemein":
            row = anteil_row_bestimmen(stadttyp, row, col, df_bev, 2.5)
        # Da 2,5 fache Anzahl an Strecken in I -> Faktor 2,5
        elif is_number(row[col]) and name[0] == "L" and col[0] != "Allgemein":
            row = anteil_row_bestimmen(stadttyp, row, col, df_bev, 2)

    return row


def bev_berechnen(df, df_bev):
    """bev_berechnen(df, df_bev)

    """
    df_new = pd.DataFrame(columns=df.columns)
    df_tmp = pd.DataFrame(columns=df.columns)
    for _, group in df.groupby([
            ("Allgemein", "Strecken_Typ"),
            "Stadttypen",
            "Modal_Choice"]):
        df_new = df_new.append(group.agg(mean_str), ignore_index=True)

    for name, group in df_new.groupby([
            ("Allgemein", "Strecken_Typ"),
            "Modal_Choice"]):
        df_tmp = df_tmp.append(group.apply(lambda row: f3(
            row, df, df_bev, name), axis=1).agg(sum_str), ignore_index=True)

    df_tmp = df_tmp.drop(columns="Stadttypen")

    return df_tmp


def f4(col, szeanrio_base, df):
    if is_numeric_dtype(col):
        col = (1 - col/df.loc[:, (szeanrio_base, col.name[1])])
    return col



def combine_pods_and_basis(df):
    return df.loc[~df.loc[:, ("Pod", "mode_1")].isin(oev_list)
                  & ~df.loc[:, ("Pod", "mode_2")].isin(oev_list)
                  & ~df.loc[:, ("Pod", "mode_2")].isin(oev_list)
                  & ~df.loc[:, ("Pod", "mode_3")].isin(oev_list)
                  & ~df.loc[:, ("Pod", "mode_4")].isin(oev_list)
                  & ~df.loc[:, ("Pod", "mode_5")].isin(oev_list)
                  & ~df.loc[:, ("Pod", "mode_6")].isin(oev_list)]


def add_pod_small(row):
    a = row.values
    a = np.where(a == "Pod_Straße", "Pod_Straße_Small", a)
    a = np.where(a == "Pod_Schiene_Nah", "Pod_Schiene_Nah_Small", a)
    a = np.where(a == "Pod_Schiene_Fern", "Pod_Schiene_Fern_Small", a)
    return pd.Series(a)


def add_pod_big(row):
    a = row.values
    if "Pod_Straße_Small" in a:
        a = np.where(a == "Pod_Straße_Small", "Pod_Straße_Big", a)
        a = np.where(a == "Pod_Schiene_Nah_Small", "Pod_Schiene_Nah_Big", a)
        a = np.where(a == "Pod_Schiene_Fern_Small", "Pod_Schiene_Fern_Big", a)
        return pd.Series(a)
    else:
        a = np.where(a == "adfasdf", "Hallo", "Hallo")
        return pd.Series(a)


def add_pods(df_pod):
    df_pod = df_pod.apply(
        lambda row: add_pod_small(row), axis=1, result_type='broadcast'
    )
    df_tmp = df_pod.apply(
        lambda row: add_pod_big(row), axis=1, result_type='broadcast'
    )
    df_tmp = df_tmp.loc[df_tmp.loc[:, ("Pod", "Transferzeit")] != "Hallo"]
    df_pod = pd.concat([
        df_pod,
        df_tmp
    ], axis=0, ignore_index=True)

    return df_pod


def umgruppieren(df, df_pod):
    df = df.set_index([("Allgemein", "Strecken_Typ"), "Modal_Choice"])
    df_pod = df_pod.set_index([("Allgemein", "Strecken_Typ"), "Modal_Choice"])
    df.index = df.index.set_names('Streckentyp', level=0)
    df_pod.index = df_pod.index.set_names('Streckentyp', level=0)
    df = pd.concat([df, df_pod], axis=1)
    df = df.stack()
    df.index = df.index.set_names('Kategorien', level=2)
    df = df[["Klassisch", "Trendszenario", "Autonom", "Optimiert", "Pod"]]
    return df


def umgruppieren_gv(df, df_pod):
    df = df.set_index([("Allgemein", "Strecken_Typ"), "Modal_Choice"])
    df_pod = df_pod.set_index([("Allgemein", "Strecken_Typ"), "Modal_Choice"])
    df.index = df.index.set_names('Streckentyp', level=0)
    df_pod.index = df_pod.index.set_names('Streckentyp', level=0)
    df = pd.concat([df, df_pod], axis=1)
    df = df.drop(columns=[("Allgemein", "Name_Verbindung")])
    df = df.stack()
    df.index = df.index.set_names('Kategorien', level=2)
    df = df[["Klassisch", "Trendszenario", "Autonom", "Optimiert", "Pod"]]
    return df


def umbennenungen_gv(df_tmp):
    df_tmp.loc[:, "Modal_Choice"] = pd.Series(
        [""] + ["Kombiniert", "Kombiniert", "Direktlauf"]*2
    )

    grouped = df_tmp.groupby(by=[("Allgemein", "Name_Verbindung")])

    df_ausgabe = pd.DataFrame(columns=df_tmp.columns)

    for _, group in grouped:
        df_ausgabe = df_ausgabe.append(
            group.loc[
                group.loc[:, "Modal_Choice"] == "Kombiniert"
            ].agg(mean_str),
        )
        df_ausgabe = df_ausgabe.append(
            group.loc[
                group.loc[:, "Modal_Choice"] == "Direktlauf"
            ]
        )

    return df_ausgabe


def pods_einbinden(datenbasis):
    datenbasis["rf_pv_Pod"].df = datenbasis["rf_pv_Pod"].df.append(
        combine_pods_and_basis(
            datenbasis["rf_pv_Basis"].df.rename(
                columns={"Klassisch": "Pod"}
            )
        ),
        ignore_index=True
    )

    datenbasis["rf_pv_Pod"].df = add_pods(
        datenbasis["rf_pv_Pod"].df)

    return datenbasis


def main():
    wb = xw.Book.caller()  # init Workbook Object

    """Forbereitung der Datenbanken
    """
    db = bekanntmachen(wb)
    dfs = extract_DataFrames(db)
    szenarios = get_szenarios(db) + ["Pod"]
    kategorien = get_kategorien(db)
    datenbasis = conv_db_in_format(dfs)

    datenbasis = pods_einbinden(datenbasis)  # add Pods
    """Personenverkehr
    Führt alle
    """
    for szenario in szenarios:
        name_db = "rf_pv_" + szenario
        if name_db not in datenbasis.keys():
            datenbasis[name_db] = pd.DataFrame()
        # Tabelle Klassisch == Szenarien
        if not szenario == "Pod":
            datenbasis[name_db].df = datenbasis["rf_pv_Basis"].df.copy()
            datenbasis[name_db].df = datenbasis[name_db].df.rename(
                columns={"Klassisch": szenario})

        datenbasis[name_db].df.sort_values(
            by=[("Allgemein", "Name_Verbindung")], inplace=True)
        datenbasis[name_db].df = datenbasis[name_db].df.reset_index(drop=True)

        # Anpassen der Zeiten und Längen
        datenbasis[name_db].df = rf_strecken_anpassungen(
            datenbasis[name_db].df,
            datenbasis["Anpassungen_rf"].df,
            szenario)
        # Bestimmen der Kosten je Verkehrsmittel
        datenbasis[name_db].df = datenbasis[name_db].df.apply(
            lambda row: kosten_bestimmen(
                row,
                datenbasis["Technologiedaten"].df,
                szenario),
            axis=1)
        # Bestimmen der Emissionen je Weg
        df_tmp = emissionen_bestimmen(
            datenbasis[name_db].df,
            datenbasis["Technologiedaten"].df,
            kategorien,
            szenario)

        grouped = df_tmp.groupby(level=0, axis=1)

        if szenario == "Klassisch":
            datenbasis["erg_pv"].df = grouped.get_group(
                "Allgemein")
            datenbasis["erg_pv"].df = pd.concat(
                [datenbasis["erg_pv"].df,
                    grouped.get_group("Modal_Choice")],
                axis=1,
                ignore_index=False)
            datenbasis["erg_pv"].df = pd.concat(
                [datenbasis["erg_pv"].df,
                    grouped.get_group(szenario)],
                axis=1,
                ignore_index=False)
        elif szenario != "Pod":
            datenbasis["erg_pv"].df = pd.concat(
                [datenbasis["erg_pv"].df,
                    grouped.get_group(szenario)],
                axis=1,
                ignore_index=False)

    # anpassen der Stadttypen in einer Spalte
    datenbasis["erg_pv"].df = datenbasis["erg_pv"].df.apply(
        lambda row: build_cities(
            row,
            datenbasis["erg_pv"].df,
            datenbasis["rf_pv_Strecken"].df,
            datenbasis["Staedte"].df),
        axis=1)
    df_tmp = df_tmp.apply(lambda row: build_cities(
        row,
        df_tmp, datenbasis["rf_pv_Strecken"].df,
        datenbasis["Staedte"].df),
        axis=1)
    # Einfügen der Marktanteile im Fahrradmarkt
    datenbasis["erg_pv"].df = rad_berechnen(
        datenbasis["erg_pv"].df,
        datenbasis["Informationen_Rad"].df,
        "Klassisch"
    )
    df_tmp = rad_berechnen(
        df_tmp, datenbasis["Informationen_Rad"].df, "Pod")
    # Zusammenführen mit Hilfe der Stadtanteile
    datenbasis["erg_pv"].df = bev_berechnen(
        datenbasis["erg_pv"].df,
        datenbasis["Bevoelkerungsverteilung"].df)
    df_tmp = bev_berechnen(
        df_tmp, datenbasis["Bevoelkerungsverteilung"].df)

    datenbasis["erg_pv"].df = umgruppieren(
        datenbasis["erg_pv"].df,
        df_tmp
    )

    grouped = datenbasis["erg_pv"].df.groupby(
        by=["Streckentyp", "Modal_Choice"]
    )
    for key, group in grouped:
        if key[1] in ["MIV", "Fahrrad", "Flugzeug"]:
            vals = group.loc[:, "Optimiert"].values
            datenbasis["erg_pv"].df.loc[(
                key[0], key[1], slice(None)), "Pod"] = vals

    """Güterverkehr
    Führt alle modifikationen an den Güterverkehr Tabellen durch.
    """
    for szenario in szenarios:
        name_db = "rf_gv_" + szenario
        if name_db not in datenbasis.keys():
            datenbasis[name_db] = pd.DataFrame()
        # Tabelle Klassisch == Szenarien
        if not szenario == "Pod":
            datenbasis[name_db].df = datenbasis["rf_gv_Basis"].df
            datenbasis[name_db].df = datenbasis[name_db].df.rename(
                columns={"Klassisch": szenario})
        # Anpassen der Zeiten und Längen
        datenbasis[name_db].df = rf_strecken_anpassungen(
            datenbasis[name_db].df,
            datenbasis["Anpassungen_rf"].df,
            szenario)
        # Bestimmen der Kosten je Verkehrsmittel
        datenbasis[name_db].df = datenbasis[name_db].df.apply(
            lambda row: kosten_bestimmen(
                row,
                datenbasis["Technologiedaten"].df,
                szenario),
            axis=1)
        # Bestimmen der Emissionen je Weg
        df_tmp = emissionen_bestimmen(
            datenbasis[name_db].df,
            datenbasis["Technologiedaten"].df,
            kategorien,
            szenario)

        grouped = df_tmp.groupby(level=0, axis=1)

        if szenario == "Klassisch":
            datenbasis["erg_gv"].df = grouped.get_group(
                "Allgemein")
            datenbasis["erg_gv"].df = pd.concat(
                [datenbasis["erg_gv"].df,
                    grouped.get_group("Modal_Choice")],
                axis=1,
                ignore_index=False)
            datenbasis["erg_gv"].df = pd.concat(
                [datenbasis["erg_gv"].df,
                    grouped.get_group(szenario)],
                axis=1,
                ignore_index=False)
        elif szenario != "Pod":
            datenbasis["erg_gv"].df = pd.concat(
                [datenbasis["erg_gv"].df,
                    grouped.get_group(szenario)],
                axis=1,
                ignore_index=False)

    datenbasis["erg_gv"].df = umbennenungen_gv(
        datenbasis["erg_gv"].df
    ).reset_index(drop=True)

    df_tmp.loc[:, "Modal_Choice"] = ["Kombiniert",
                                     "Direktlauf", "Kombiniert", "Direktlauf"]

    datenbasis["erg_gv"].df = umgruppieren_gv(
        datenbasis["erg_gv"].df,
        df_tmp
    )

    """Write back!
    Schreiben der bearbeiteten Tabellenblätter in die Excel.
    """
    changed = ["erg_pv", "erg_pv"]
    for name in changed:
        print_DataFrame(name, datenbasis[name].df, db, wb)

    autofit(wb)


if __name__ == "__main__":
    xw.Book("190910_Bewertungstool_v03.xlsm").set_mock_caller()

    #main()

    wb = xw.Book.caller()  # init Workbook Object

    db = bekanntmachen(wb)
    dfs = extract_DataFrames(db)
    szenarios = get_szenarios(db) + ["Pod"]
    kategorien = get_kategorien(db)
    datenbasis = conv_db_in_format(dfs)

    datenbasis = pods_einbinden(datenbasis)  # add Pods

    for name, df in datenbasis.items():
        print(df.df)
