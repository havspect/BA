import json

def save_dict(path, name):
    with open("{0}.json".format(name), "w") as f:
        json.dump(path, f)
    
def load_dict(name):
    with open("{0}.json".format(name)) as f:
        return json.load(f)

def eingabe_verbindungen():
    mode = input("Verkehrsmittel: ")
    mode_length = input("Länge Verkehrsmittel: ")
    mode_time = input("Transferzeit Verkehrsmittel: ")
    mode_wartezeit = input("Wartezeit: ")
    tmp = {
        "Verkehrsmittel": mode,
        "Laenge": int(mode_length),
        "Fahrtzeit": int(mode_time),
        "Wartezeit": int(mode_wartezeit),
    }
    return tmp


def extract_kombinationen():
    tmp = True
    tmp_ges = True
    kombi = list()
    kombi_ges = list()
    while tmp_ges:
        while tmp:
            kombi.append(eingabe_verbindungen())
            tmp = input("Weitere Verkehrsmittel in Kombination? (1)")
            if int(tmp) == 1:
                tmp = True
            else:
                tmp = False
        kombi_ges.append(kombi)
        kombi = list()
        tmp_ges = input("Weitere Kombination? (1)")
        if int(tmp_ges) == 1:
            tmp_ges = True
            tmp = True
        else: 
            tmp_ges = False
    return kombi_ges


def add_part(kombis, gesamt):
    for part in kombis:
        if part["Verkehrsmittel"] in gesamt.keys():
            tmp = gesamt[part["Verkehrsmittel"]] 
            gesamt[part["Verkehrsmittel"]] = { k: tmp.get(k, 0) + part.get(k, 0) for k in set(tmp) & set(part) }
        else:
            gesamt[part["Verkehrsmittel"]] = {
                "Laenge": part["Laenge"],
                "Fahrtzeit": part["Fahrtzeit"],
                "Wartezeit": part["Wartezeit"],
            }
    return gesamt


def kombi(start_kombi, main_kombi, ziel_kombi):
    kombinationen = list()
    for start in start_kombi:
        for main in main_kombi:
            for ziel in ziel_kombi:
                gesamt = dict()
                gesamt = add_part(start, gesamt)
                gesamt = add_part(main, gesamt)
                gesamt = add_part(ziel, gesamt)
                kombinationen.append(gesamt)
    return kombinationen
                    

print("Bitte geben sie die Kombinationen zum Zwischenziel (Start) ein:")
start_kombi = extract_kombinationen()
save_dict(start_kombi, "start")

print("Bitte geben sie die Kombinationen von Start zu Ziel ein:")
main_kombi = extract_kombinationen()
save_dict(main_kombi, "main")

print("Bitte geben sie die Kombinationen vom Zwischenziel (Ziel) zum Ziel an:")
ziel_kombi = extract_kombinationen()
save_dict(ziel_kombi, "ziel")

# start_kombi = load_dict("start")
# main_kombi = load_dict("main")
# ziel_kombi = load_dict("ziel")

erg = kombi(start_kombi, main_kombi, ziel_kombi)

def ausgabe(route, ft, wt, gt, length):
    my_dict = dict()
    my_dict["Gesamt Zeit"] = gt
    my_dict["Wartezeit"] = wt
    my_dict["Fahrtzeit"] = ft
    my_dict["Laenge"] = length
    for key, val in route.items():
        print('\t' + key + '\t'+ str(val["Laenge"]))
        my_dict[key] = key
        my_dict[key + "length"] = val["Laenge"]
    return my_dict

def csv_ausgabe(list_ausgabe):
    tmp = ""
    with open("ausgabe.csv", "w") as f:
        for entry in list_ausgabe:
            for _, val in entry.items():
                tmp += str(val) + ","
            f.write(tmp[:-1] + "\n")
            tmp = ""

list_ausgabe = list()
for route in erg:
    wt = 0
    length = 0
    ft = 0
    gt = 0
    for _, vals in route.items():
        wt += vals["Wartezeit"]
        length += vals["Laenge"]
        ft += vals["Fahrtzeit"]
        gt += (vals["Fahrtzeit"] + vals["Wartezeit"])
    print("Fahrtzeit: {0}, Wartezeit: {1}, gesamte Zeit: {2}, Länge {3}".format(ft, wt, gt, length))
    list_ausgabe.append(ausgabe(route, ft, wt, gt, length))
    csv_ausgabe(list_ausgabe)










