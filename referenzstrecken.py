import numpy as np
import pandas as pd
import xlwings
from pandas.api.types import is_numeric_dtype
import subprocess
import os

from datenbasis_funktionen import *

oev_list = ["Bus", "Tram", "U-Bahn", "Zug-Nahverkehr", "Zug-Fernverkehr"]

per_trip_costs = ["Bus", "Tram", "U-Bahn", "Flugzeug"]


def rf_strecken_anpassungen(df, df_anpassungen, szenario):
    modes = [("mode_{0}".format(i), "mode_costs_{0}".format(
        i), "mode_length_{0}".format(i), "mode_factor_length_{0}".format(i),
        "mode_factor_time_{0}".format(i), "mode_factor_wtime_{0}".format(i)) for i in range(1, 6 + 1)]
    for mode in modes:
        # Aufbau der Cols mit den Faktoren aus Tabelle Anpassungen
        df[mode[3]] = [df_anpassungen.loc[(x, "Length"), szenario] if x in df_anpassungen.index.get_level_values(
            0) else 1 for x in df[(szenario, mode[0])]]
        df[mode[4]] = [df_anpassungen.loc[(x, "Fahrtzeit"), szenario] if x in df_anpassungen.index.get_level_values(
            0) else 1 for x in df[(szenario, mode[0])]]
        df[mode[5]] = [df_anpassungen.loc[(x, "Wartezeit"), szenario] if x in df_anpassungen.index.get_level_values(
            0) else 1 for x in df[(szenario, mode[0])]]
        # Anpassungen der Streckenlänge
        df[(szenario, mode[2])] *= df[mode[3]]
        df = df.drop([mode[3]], axis=1)
    # Bestimmen der neuen Gesamtlänge
    li = [(szenario, "mode_length_{0}".format(i)) for i in range(1, 6 + 1)]
    df[(szenario, "Length")] = df.loc[:, li].sum(axis=1)

    # Anpassen der Faktoren mit den Streckenanteilen
    for mode in modes:
        df.loc[:, mode[4]] *= (df.loc[:, (szenario, mode[2])] /
                               df.loc[:, (szenario, "Length")])
        df.loc[:, mode[5]] *= (df.loc[:, (szenario, mode[2])] /
                               df.loc[:, (szenario, "Length")])
    # Multiplikation der Fahrzeit mit dem Gesamtfaktor und löchen der Hilfscols
    li = ["mode_factor_time_{0}".format(i) for i in range(1, 6 + 1)]
    df[(szenario, "Fahrtzeit")] *= df[li].sum(axis=1)
    df = df.drop(li, axis=1)
    # Multiplikation Wartezeit mit Gesamtfaktor und löchen der Hilfscols
    li = ["mode_factor_wtime_{0}".format(i) for i in range(1, 6 + 1)]
    df[(szenario, "Wartezeit")] *= df[li].sum(axis=1)
    df = df.drop(li, axis=1)
    # Zusammenfügen zur neuen Gesamtfahrzeit
    df[(szenario, "Transferzeit")] = df[(szenario, "Fahrtzeit")] + \
        df[(szenario, "Wartezeit")]

    return df


def szenario_anpassungen(df, szenario, df_anpassungen):
    df = df.apply(lambda row: szenario_anpassungen_row(
        row, szenario, df_anpassungen), axis=1)
    return df


def spezifische_kosten_bestimmen(verkehrsmittel, df, verkehrsmittel_length, szenario):
    """Bestimmt die Kosten in Abhängigkeit von per_trip or per_costs.
    """
    if verkehrsmittel in per_trip_costs:
        return df.loc[(verkehrsmittel, "Kosten"), szenario]
    else:
        return df.loc[(verkehrsmittel, "Kosten"), szenario] \
            * verkehrsmittel_length


def kosten_bestimmen(row, df, szenario):
    modes = [("mode_{0}".format(i), "mode_costs_{0}".format(
        i), "mode_length_{0}".format(i)) for i in range(1, 6 + 1)]

    for mode in modes:
        if (isinstance(row[szenario].loc[mode[0]], (str)) and not
                row[szenario].loc[mode[0]] == "" and not
                row[szenario].loc[mode[0]] is None and
                "Pod_" not in row[szenario].loc[mode[0]]):
            row[szenario].loc[mode[1]] = spezifische_kosten_bestimmen(
                row[szenario].loc[mode[0]],
                df,
                (int(row[szenario].loc[mode[2]])/1000),
                szenario)

        else:
            break

    return row


def how_to_add(row, tmp, verkehrsmittel, mode, szenario):
    """how_to_add(row, tmp, verkehrsmittel, mode)
    Für die anteilige Berechnung der Verkehrsmittel wird ermittelt, welches
    Verkehrsmittel den größten Anteil an der Gesamtstrecke hat.
    Dafür müssen zunächst die Verkehrsmittel dem dict hinzugefügt werden.

    """
    if verkehrsmittel in tmp.keys():
        tmp[verkehrsmittel] += row[(szenario, mode[2])]
    else:
        tmp[verkehrsmittel] = row[(szenario, mode[2])]
    return tmp


def f1(row, modes, szenario):
    """f3(row)
    Verkehrsmittel in eine Spalte schreiben und Verkehrsmittel des
    ÖV zusammenfassen.

    """
    tmp = dict()
    for mode in modes:
        if row[(szenario, mode[0])] in oev_list:
            tmp = how_to_add(row, tmp, "ÖV", mode, szenario)

        elif row[(szenario, mode[0])] == "Pod_Straße_Small":
            tmp = how_to_add(row, tmp, "Pod_Small", mode, szenario)
            tmp["Pod_Small"] = 10000000
            break

        elif row[(szenario, mode[0])] == "Pod_Straße_Big":
            tmp = how_to_add(row, tmp, "Pod_Big", mode, szenario)
            tmp["Pod_Big"] = 10000000
            break

        elif row[(szenario, mode[0])] == "MIV":
            tmp = how_to_add(row, tmp, "MIV", mode, szenario)

        elif row[(szenario, mode[0])] in ["E-Bike", "Fahrrad"]:
            tmp = how_to_add(row, tmp, "Fahrrad", mode, szenario)

        elif isinstance(row[(szenario, mode[0])], str):
            tmp = how_to_add(
                row, tmp, row[(szenario, mode[0])], mode, szenario)

    mode_max = max(tmp, key=tmp.get)
    if mode_max == "zu Fuss" and len(tmp) > 1:
        tmp.pop('zu Fuss', None)
        mode_max = max(tmp, key=tmp.get)
    return mode_max


def spezfisiche_emissionen_weg(row, df, modes, kategorien, szenario):
    """spezfisiche_emissionen_weg(row, df, modes, kategorien, szenarios)
    Berechnet die spezifischen Emissionen für jede einzelne Strecke.
    """
    exceptions_kategorien = [
        "Verfuegbarkeit",
        "Transferzeit",
        "Wartezeit",
        "Fahrtzeit",
        "Length"]
    for kategorie in kategorien:
        if kategorie not in exceptions_kategorien:
            tmp = 0
            for mode in modes:
                if (isinstance(row[(szenario, mode[0])], (str)) and not
                        row[(szenario, mode[0])] == ""):
                    verkehrsmittel = row[(szenario, mode[0])]
                    verkehrsmittel_length = row[(
                        szenario, mode[2])] / 1000  # in km
                    verkehrsmittel_costs = row[(szenario, mode[1])]
                else:
                    verkehrsmittel = "empty"
                    break

                if (kategorie == "Kosten" and
                        isinstance(verkehrsmittel_costs, (int, float))):
                    tmp += verkehrsmittel_costs

                elif kategorie != "Unfallrisiko":
                    # Länge der Teilstrecke mal den spezifischen Werten.
                    tmp += verkehrsmittel_length \
                        * df.loc[(verkehrsmittel, kategorie), szenario]
                else:
                    # Unfallrisiko ist auf 1 Mrd. Pkm/Tkm bezogen
                    tmp += ((verkehrsmittel_length * 1000)
                            / row[(szenario, "Length")]) \
                            * df.loc[(verkehrsmittel, kategorie), szenario]

            row.loc[(szenario, kategorie)] = tmp  # abspeichern in der Row

        elif not kategorie == "Verfuegbarkeit":
            row.loc[(szenario, kategorie)] = row[(szenario, kategorie)]

    return row


def emissionen_bestimmen(df, df_technologie, kategorien, szenario):
    """emissionen_bestimmen(df, df_technologie, kategorien, szenario)


    """
    modes = [("mode_{0}".format(i), "mode_costs_{0}".format(
        i), "mode_length_{0}".format(i)) for i in range(1, 6 + 1)]

    # Emissionen je Weg bestimmen
    df = df.apply(lambda row: spezfisiche_emissionen_weg(
        row, df_technologie, modes, kategorien, szenario), axis=1)

    # Bestimmen des Hautpverkehrsmittels je Row
    df["Modal_Choice"] = df.apply(lambda row: f1(row, modes, szenario), axis=1)

    modes_cols = [(szenario, mode[0]) for mode in modes] + \
        [(szenario, mode[1]) for mode in modes] + \
        [(szenario, mode[2]) for mode in modes]
    df = df.drop(columns=modes_cols)

    return df


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


def is_number(num):
    """is_number(num)
    Testet ob eine Zahl wirklich eine Nummer ist durch Umwandlung
    in einen float. Gibt einen Boolean zurück.
    """
    try:
        float(num)
        return True
    except:
        return False


def f2(row, df, df_rad, szenario):
    """f2(row, df, df_rad)
    Rechnet die Marktanteile von E-Bike und Fahrrad ein.
    Gibt die modifizierte Row zurück.
    """
    if row[(szenario, "THG")] > 0:
        tmp = True
    else:
        tmp = False

    for col in df.columns.tolist():
        if col[0] == "Klassisch":
            if tmp and is_number(row[col]):
                row[col] *= (df_rad.loc["E-Bike", (2017, "Anzahl")]) / \
                    df_rad[2017, "Anzahl"].loc["Rad_insgesamt"]
            elif is_number(row[col]):
                row[col] *= (df_rad.loc["Rad_insgesamt", (2017, "Anzahl")]
                             / df_rad[2017, "Anzahl"].loc["Rad_insgesamt"])
        else:
            if tmp and is_number(row[col]):
                row[col] *= (df_rad.loc["E-Bike", (2050, "Anzahl")]
                             / df_rad[2050, "Anzahl"].loc["Rad_insgesamt"])
            elif is_number(row[col]):
                row[col] *= (df_rad.loc["Rad_insgesamt", (2050, "Anzahl")]
                             - df_rad.loc["E-Bike", (2050, "Anzahl")]) \
                    / df_rad[2050, "Anzahl"].loc["Rad_insgesamt"]

    return row


def sum_str(col):
    """sum_str(col)
    Berechnet die Summe für ein Column und ignoriert dabei Spalten, welche
    nicht numerisch sind. Bei diesen Werten, wenn die Werte gleich sind
    diese übernommen und sonst np.NaN ausgegeben.
    """
    if is_numeric_dtype(col):
        return col.sum()
    else:
        return col.unique() if col.nunique() == 1 else np.NaN


def mean_str(col):
    """mean_str(col)
    Berechnet den Mittelwert für ein Column und ignoriert dabei Spalten, welche
    nicht numerisch sind.Bei diesen Werten, wenn die Werte gleich sind diese
    übernommen und sonst np.NaN ausgegeben.
    """
    if is_numeric_dtype(col):
        return col.mean()
    else:
        return col.unique() if col.nunique() == 1 else np.NaN


def rad_berechnen(df, df_rad, szenario):
    """rad_berechnen(df, df_rad)
    Berechnet die spezifischen Emissionen für die Rad-Strecken.
    Gibt den df: pd.DataFrame zurück.
    """
    df = df.loc[df.loc[:, ("Allgemein", "Name_Verbindung")] != np.NaN]
    grouped = df.groupby([("Allgemein", "Name_Verbindung"), "Modal_Choice"])
    index_names = df.loc[df["Modal_Choice"] == "Fahrrad"].index
    df_new = df.copy()
    df_new = df_new.drop(index_names)
    for name, group in grouped:
        if name[1] == "Fahrrad":
            df_new = df_new.append(group.apply(lambda row: f2(
                row, df, df_rad, szenario), axis=1).agg(sum_str),
                ignore_index=True)
    df_new = df_new.drop(columns=("Allgemein", "Name_Verbindung"))
    return df_new


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


def verbesserunge_zu_szenario(df, szenario_base, styp=False):
    """verbesserunge_zu_klassisch(df)

    Part 1: Nimmt die berechneten Werte für die Emissionen
    und Kosten und setzt sie ins Verhältnis zu den Klassischen Werten!
    Part 2: Nimmt die berechneten Werte für die Emissionen
    und Kosten und setzt diese ins Verhältnis zu den Trendszenario Werten!
    """
    grouped = df.groupby(level=0, axis=1)
    df_new = pd.DataFrame()  # init empty DataFrame

    reihenfolge = [df_new,
                   grouped.get_group("Allgemein"),
                   grouped.get_group("Modal_Choice"),
                   ]
    if not styp:
        reihenfolge.append(grouped.get_group("Stadttypen"))

    df_new = pd.concat(reihenfolge, axis=1, ignore_index=False)

    exceptions_list = ["Allgemein", "Klassisch", "Stadttypen", "Modal_Choice"]
    if szenario_base != "Klassisch":
        exceptions_list = ["Allgemein", "Klassisch",
                           "Stadttypen", "Modal_Choice"] + [szenario_base]

    for name, group in grouped:
        if name not in exceptions_list:
            df_new = pd.concat([df_new, group.transform(
                lambda col: f4(col, szenario_base, df))],
                axis=1,
                ignore_index=False)

    return df_new


def verbesserunge_zu_szenario_gesamt(datenbasis, wb):
    for szenario in ["Klassisch", "Trendszenario"]:
        df_tmp = verbesserunge_zu_szenario(
            datenbasis["Ergebnisse_Personenverkehr"].df, szenario)
        df_tmp_staedte = verbesserunge_zu_szenario(
            datenbasis["Ergebnisse_Personenverkehr_städte"].df,
            szenario,
            styp=True)
        sht_tmp = create_sheet(wb, "rf_pv_erg_ver_" + szenario, activate=False)
        sht_tmp_styp = create_sheet(
            wb, "rf_pv_erg_styp_" + szenario, activate=False)
        sht_tmp.range("A1").value = df_tmp
        sht_tmp_styp.range("A1").value = df_tmp_staedte


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
