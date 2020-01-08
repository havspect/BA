import xlwings as xw
import pandas as pd
from datenbasis_funktionen import *

szenarios = ["Trendszenario", "Autonom", "Pod"]


def improvement_cell_szenario(row, szenario, dfs):
    if szenario == "Trendszenario":
        szenario_base = "Klassisch"
        if dfs["Verbesserungsfaktoren"].loc[row.name, (szenario, "ist_Strom")] == "ja":
            ist_strom = True
        else:
            ist_strom = False
    else:
        szenario_base = "Trendszenario"
        ist_strom = False

    if ist_strom and row.name[1] == "Energieverbrauch":
        tmp = row[szenario_base] * dfs["Verbesserungsfaktoren"].loc[(
            row.name[0], "Energieverbrauch"), (szenario, "Faktor")]
    elif ist_strom:
        tmp = dfs["Technologiedaten"].loc[(row.name[0], "Energieverbrauch"), szenario_base] \
            * dfs["Verbesserungsfaktoren"].loc[(row.name[0], "Energieverbrauch"), (szenario, "Faktor")] \
            * dfs["Bevoelkerungs_und_Emissiondaten"].loc["spez_Emissionsfaktor_{0}".format(row.name[1]), 2050]
    elif isinstance(dfs["Verbesserungsfaktoren"].loc[row.name, (szenario, "Faktor")], (int, float)):
        tmp = dfs["Verbesserungsfaktoren"].loc[row.name,
                                               (szenario, "Faktor")] * row[szenario_base]

    return tmp


def f1(row, dfs):
    for i in ["Trendszenario", "Autonom", "Optimiert", "Pod"]:
        if "Pod_" not in row.name[0]:
            row[i] = improvement_cell_szenario(row, i, dfs)
    return row


def main():
    wb = xw.Book.caller()

    db = bekanntmachen(wb)
    dfs = extract_DataFrames(db)
    dfs["Technologiedaten"] = dfs["Technologiedaten"].apply(
        lambda row: f1(row, dfs), axis=1)

    print_DataFrame(
        "Technologiedaten",
        dfs["Technologiedaten"],
        db,
        wb
    )

    autofit(wb)


if __name__ == "__main__":
    xw.Book("190910_Bewertungstool_v03.xlsm").set_mock_caller()
    main()
