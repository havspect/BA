import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import os
from datenbasis_funktionen import *


def autolabel(rects, ax):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = np.round(rect.get_height(), 2)
        if height > 0:
            ax.annotate('{}'.format(height),
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')
    return ax


def plot_bars(df_auswertung, kategorie, streckentyp, sht):
    x = np.arange(len(df_auswertung.index))
    width = 0.18
    alpha = 1
    colors = ["#292929", "#4d4d4d", "#717171", "#959595", "#b9b9b9"]

    if streckentyp == "I":
        streckentyp = "Intercity"
    elif streckentyp == "L":
        streckentyp = "Langstrecke"
    elif streckentyp == "UL":
        streckentyp = "Urban-Langstrecke"
    elif streckentyp == "UK":
        streckentyp = "Urban-Kurzstrecke"

    # fig, ax = plt.subplots(figsize = [8, 4.8])
    fig = plt.figure(figsize=[9, 4.8])
    ax = plt.subplot(111)

    rects1 = ax.bar(
        x - 10*width/5,
        df_auswertung["Klassisch"],
        width=width,
        alpha=alpha,
        label="Klassisch",
        color=colors[0],
        linewidth=0
    )
    rects2 = ax.bar(
        x - 5*width/5,
        df_auswertung["Trendszenario"],
        width=width,
        alpha=alpha,
        label="Trendszenario",
        color=colors[1],
        linewidth=0
    )
    rects3 = ax.bar(
        x,
        df_auswertung["Autonom"],
        width=width,
        alpha=alpha,
        label="Autonom",
        color=colors[2],
        linewidth=0
    )
    rects4 = ax.bar(
        x + 5*width/5,
        df_auswertung["Optimiert"],
        width=width,
        alpha=alpha,
        label="Optimierte Multimodale Mobilität",
        color=colors[3],
        linewidth=0
    )
    rects5 = ax.bar(
        x + 10*width/5,
        df_auswertung["Pod"],
        width=width,
        alpha=alpha,
        label="Pod-Szenario",
        color=colors[4],
        linewidth=0
    )

    ax.set_xticks(x)
    if kategorie in ["THG", "PM", "NOx"]:
        ax.set_title(streckentyp + ": " + kategorie + "-Emissionen")
        ax.set_ylabel("g/Tkm")
    elif kategorie == "Energieverbrauch":
        ax.set_title(streckentyp + ": " + kategorie)
        ax.set_ylabel("MJ/Tkm")
    elif kategorie in ["Fahrtzeit", "Transferzeit", "Wartezeit"]:
        ax.set_title(streckentyp + ": " + kategorie)
        ax.set_ylabel("min")
    elif kategorie == "Unfallrisiko":
        ax.set_title(streckentyp + ": " + kategorie)
        ax.set_ylabel("Unfallrisiko je 1 Mrd. Pkm")
    elif kategorie == "Length":
        ax.set_title(streckentyp + ": " + "Streckenlänge")
        ax.set_ylabel("Länge [m]")
    elif kategorie == "Kosten":
        ax.set_title(streckentyp + ": " + "Kosten pro Weg")
        ax.set_ylabel("Kosten [Euro]")
    else:
        ax.set_title(kategorie)
        ax.set_ylabel(kategorie)

    ax.set_xticklabels(df_auswertung.index)

    # Einfügen der Legende an der Seite
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))

    # Einfügen von vertikalen Grid Lines
    ax.set_axisbelow(True)
    ax.yaxis.grid(color="black", linestyle='-', linewidth=0.4)

    fig.tight_layout()
    plt.subplots_adjust(bottom=0.28)
    plt.setp(ax.get_xticklabels(), rotation=90)
    plt.savefig("./plots/" + streckentyp + kategorie)

    plot = sht.pictures.add(
        plt.gcf(), name=streckentyp + kategorie, update=True)


def create_plots(df, sht):
    for y in df.index.get_level_values(0).drop_duplicates():
        df_vorauswahl = df.xs(y, level="Streckentyp")
        for x in df.index.get_level_values(2).drop_duplicates():
            if not x == "Auslastung" and not x == "Unfallrisiko":
                try:
                    df_auswertung = df_vorauswahl.xs(x, level="Kategorien")
                    plot_bars(df_auswertung, x, y, sht)
                except:
                    pass


def plot_basics(df, fig, ax, streckentyp, kategorie):
    x = np.arange(len(df.index.get_level_values(1).values))
    width = 0.18
    alpha = 1
    colors = ["#292929", "#4d4d4d", "#717171", "#959595", "#b9b9b9"]

    lines = list()

    if streckentyp == "I":
        streckentyp = "Intercity"
    elif streckentyp == "L":
        streckentyp = "Langstrecke"
    elif streckentyp == "UL":
        streckentyp = "Urban-Langstrecke"
    elif streckentyp == "UK":
        streckentyp = "Urban-Kurzstrecke"

    l1 = ax.bar(
        x - 10*width/5,
        df["Klassisch"],
        width=width,
        alpha=alpha,
        label="Klassisch",
        color=colors[0],
        linewidth=0
    )
    lines.append(l1)
    l2 = ax.bar(
        x - 5*width/5,
        df["Trendszenario"],
        width=width,
        alpha=alpha,
        label="Trendszenario",
        color=colors[1],
        linewidth=0
    )
    lines.append(l2)
    l3 = ax.bar(
        x,
        df["Autonom"],
        width=width,
        alpha=alpha,
        label="Autonom",
        color=colors[2],
        linewidth=0
    )
    lines.append(l3)
    l4 = ax.bar(
        x + 5*width/5,
        df["Optimiert"],
        width=width,
        alpha=alpha,
        label="Optimierte Multimodale Mobilität",
        color=colors[3],
        linewidth=0
    )
    lines.append(l4)
    l5 = ax.bar(
        x + 10*width/5,
        df["Pod"],
        width=width,
        alpha=alpha,
        label="Pod-Szenario",
        color=colors[4],
        linewidth=0
    )
    lines.append(l5)
    labels = df.index.get_level_values(1).values.tolist()
    labels = [labels[0]] + labels
    ax.set_xticklabels(labels)

    if kategorie in ["THG", "PM", "NOx"]:
        ax.set_title(streckentyp + ": " + kategorie + "-Emissionen")
        ax.set_ylabel("g")
    elif kategorie == "Energieverbrauch":
        ax.set_title(streckentyp + ": " + kategorie)
        ax.set_ylabel("MJ")
    elif kategorie in ["Fahrtzeit", "Transferzeit", "Wartezeit"]:
        ax.set_title(streckentyp + ": " + kategorie)
        ax.set_ylabel("Zeit [min]")
    elif kategorie == "Unfallrisiko":
        ax.set_title(streckentyp + ": " + kategorie)
        ax.set_ylabel("Unfallrisiko je 1 Mrd. Pkm")
    elif kategorie == "Length":
        ax.set_title(streckentyp + ": " + "Streckenlänge")
        ax.set_ylabel("Länge [m]")
    elif kategorie == "Kosten":
        ax.set_title(streckentyp + ": " + "Kosten pro Weg")
        ax.set_ylabel("Kosten [Euro]")
    else:
        ax.set_title(kategorie)
        ax.set_ylabel(kategorie)

    # Einfügen von vertikalen Grid Lines
    ax.set_axisbelow(True)
    ax.yaxis.grid(color="black", linestyle='-', linewidth=0.4)

    # plt.setp(ax.get_xticklabels(), rotation=90)

    return fig, ax, lines


def times(df):
    grouped = df.groupby(["Kategorien", "Streckentyp"])
    # cat = ["Fahrtzeit", "Wartezeit", "Transferzeit"]
    # styp = ["UK", "UL", "I", "L"]
    cat = ["THG", "NOx", "PM", "Energieverbrauch"]
    styp = ["N", "F"]

    for streckentyp in styp:
        x = list()
        fig = plt.figure(figsize=[10, 12])
        fig.subplots_adjust(hspace=1, wspace=0.4)
        for i, name in enumerate(cat):
            i += 1
            df_tmp = grouped.get_group((name, streckentyp))
            ax = fig.add_subplot(4, 1, i)
            fig, ax, lines = plot_basics(df_tmp, fig, ax, streckentyp, name)
            i -= 1
        # Einfügen der Legende an der Seite
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, bbox_to_anchor=(1, 0), loc="lower right",
                   bbox_transform=fig.transFigure, ncol=5)
        fig.tight_layout()
        plt.savefig("./plots/" + streckentyp + "_Emissionen")


def main():
    wb = xw.Book.caller()

    sht_daten = wb.sheets["rf_gv_erg"]
    df = sht_daten.range("A1").options(
        pd.DataFrame, expand="table", header=1, index=3).value
    sht = wb.sheets["Plots"]
    create_plots(df, sht)
    times(df)


if __name__ == "__main__":
    xw.Book("190910_Bewertungstool_v03.xlsm").set_mock_caller()

    main()
