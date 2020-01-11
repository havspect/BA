import pandas as pd 
import numpy as np
import math


def lower_and_underscores(l):
    '''
    Recives a list and lowers all words. In a second step it although replaces spaces with underscores.
    '''
    return [word.lower().replace(" ", '_').replace('-', '_') for word in l]


def find_unique_modes(tech_data):
    '''
    Liest alle Verkehrsmittel aus den Technologiedaten aus.
    '''
    return tech_data.index.levels[0]


def calc_street_pod(name, var, const = None, db = None, pod_art = 'small'):
    '''
    Berechnet ausgehend von den Variablen-Werten den spezifischne Verbrauch und die Emissionen. Gibt diese Werte in der Console aus.
    '''
    
    spez_verbrauch = db.spezifischer_verbrauch
    gemis_data = db.gemis_data
    tech_data = db.technologiedaten
    
    # Berechnung Gewicht
    if var['is_elektro']:
        print('Die Berechnung wird für ein elektrisches Fahrzeug durchgeführt!')
    else:
        print('Die Berechnung wird für ein Diesel Fahrzeug durchgeführt! \nEs handelt sich dabei um keinen reinen Diesel sondern inklusive Anteilen von Hybriden.')
    print('------------------------------------------')

    if pod_art == 'small':
        gewicht_pod = var['leergewicht'] + var['zusatz_gewicht'] + (var['max_passagiere'] * var['auslastung'] * const['gewicht_PAX'])
        print(f'Anzahl an Passagieren: {round(var["max_passagiere"] * var["auslastung"], 0)}')
                                                
    elif 'cargo' in pod_art:
        var['max_passagiere'] = (const['max_gewicht'] - var['leergewicht'] - var['zusatz_gewicht'])
        gewicht_pod = var['leergewicht'] + var['zusatz_gewicht'] + (var['max_passagiere'] * var['auslastung'])
        print(f'Max. Zuladung [kg]: {var["max_passagiere"]}')
        print(f'Zuladung [kg]: {var["max_passagiere"] * var["auslastung"]}')
        var['max_passagiere'] /= 1000
        
    elif pod_art == 'big':
        print(f'Anzahl an Passagieren: {round(var["max_passagiere"] * var["auslastung"], 0)}')
    
    if pod_art in ['small', 'cargo small', 'cargo big']:
        print(f'Gesamtgewicht [kg]: {gewicht_pod}')
    
    print('------------------------------------------')                                                           
                                                                    
    # Berechnung Verbrauch
    if pod_art == 'small' or pod_art == 'cargo small':
        diesel_verbrauch = round(spez_verbrauch.loc['pro_kg', 'diesel'] / 100 * gewicht_pod,2)
        elektro_verbrauch = round((spez_verbrauch.loc['n1', 'elektro']
                            * (spez_verbrauch.loc['pro_kg', 'diesel']
                            / 100
                            * gewicht_pod) 
                            / spez_verbrauch.loc['n1', 'diesel']),2)
    elif pod_art == 'big':
        diesel_verbrauch = round(spez_verbrauch.loc['stadtbus', 'diesel'] ,2)
        elektro_verbrauch = round(spez_verbrauch.loc['stadtbus', 'elektro'] ,2)
    else:
        diesel_verbrauch = round(spez_verbrauch.loc['n3', 'diesel'] ,2)
        elektro_verbrauch = round(spez_verbrauch.loc['n3', 'elektro'] ,2)

    print('Heute') 
    print(f'Diesel Verbrauch [l/km]: {diesel_verbrauch}')
    print(f'Elektro Verbrauch [kwh/km]: {elektro_verbrauch}')
    print('------------------------------------------')

    # Fortschreibung auf das Jahr 2050
    diesel_verbrauch_2050 = round(diesel_verbrauch * (1-0.47) ,2)
    elektro_verbrauch_2050 = round(elektro_verbrauch * (1-0.18) ,2)
        
    print('2050')
    print(f'Diesel Verbrauch [l/km]: {diesel_verbrauch_2050}')
    print(f'Elektro Verbrauch [kwh/km]: {elektro_verbrauch_2050}')

    if var['is_elektro']:
        df = gemis_data.loc[:, 'elektro'] * elektro_verbrauch_2050 * 3.6 / (var['max_passagiere'] * var['auslastung']) # Umrechnung auf MJ notwendig
    else:
        df = gemis_data.loc[:, 'diesel'] * diesel_verbrauch_2050 / (var['max_passagiere'] * var['auslastung']) 
    
    
    if pod_art == "small":
        df.loc['unfallrisiko'] = tech_data.loc[('miv', 'unfallrisiko'), 'autonom']
    elif pod_art == "cargo small":
        df.loc['unfallrisiko'] = tech_data.loc[('lnutzfahrzeuge', 'unfallrisiko'), 'autonom']
    elif pod_art == 'cargo big':
        df.loc['unfallrisiko'] = tech_data.loc[('lkw', 'unfallrisiko'), 'autonom']
    else:
        df.loc['unfallrisiko'] = tech_data.loc[('bus', 'unfallrisiko'), 'autonom']
        
    if var['is_elektro']:
        df.loc['verbrauch'] = elektro_verbrauch_2050
    else:
        df.loc['verbrauch'] = diesel_verbrauch_2050
        
    df.loc['kosten'] = tech_data.loc[(name, 'kosten'), 'pod']
    
    df = pd.DataFrame(df).round(4)
    print('------------------------------------------')
    print(df.reindex(['thg', 'pm', 'nox', 'energieverbrauch', 'unfallrisiko']))
    
    df.loc['is_elektro'] = var['is_elektro']
    
    df.loc['transportmenge'] = var['max_passagiere'] * var['auslastung']
    
    return df


def add_tmp(name, df, tmp):
    for i in df.index.levels[1]:
        if i not in ['auslastung', 'verfuegbarkeit']:
            df.loc[(name, i), 'pod'] = tmp.loc[i].values[0]
    return df
            
    
def calc_costs(const, var, allgemein, pod_df, tech_data):
    
    idx = pd.IndexSlice
    
    index = ['pod_straße_small',
             'pod_straße_big',
             'pod_straße_cargo_small',
             'pod_straße_cargo_big',
             'carrier_straße_small',
             'carrier_straße_big',
             'carrier_straße_cargo_small',
             'carrier_straße_cargo_big']
    pods = [x for x in index if 'pod' in x]
    carrier = [x for x in index if 'carrier' in x]
    columns = ['anschaffungskosten',  # €
               'kosten_schnittstellen',  # €
               'kalk_kosten',  # €/km
               'energie_kosten',  # €/km
               'instandhaltung_kosten',  # €/km
               'versicherung_kosten',  # €/km
               'reifen_kosten',  # €/km
               'overhead_kosten'  # €/km
              ]
    
    df = pd.DataFrame(0, columns=columns ,index=index)  # init
    
    df.loc[pods,'kosten_schnittstellen'] = (var['schnittstelle'] * var['anzahl_schnittstellen_pod']) 
    df.loc[carrier,'kosten_schnittstellen'] = (var['schnittstelle'] * var['anzahl_schnittstellen_carrier'])
    
    # Pod Small
    df.loc['pod_straße_small', 'anschaffungskosten'] = var['costs_pod_small'] + df.loc['pod_straße_small','kosten_schnittstellen']
    # Pod Big
    df.loc['pod_straße_big', 'anschaffungskosten'] = var['costs_pod_big'] + df.loc['pod_straße_big','kosten_schnittstellen']
    
    # Pod Cargo Small
    df.loc['pod_straße_cargo_small', 'anschaffungskosten'] = var['costs_pod_cargo_small'] + df.loc['pod_straße_cargo_small','kosten_schnittstellen']
    
    # Pod Cargo Big
    df.loc['pod_straße_cargo_big', 'anschaffungskosten'] = var['costs_pod_cargo_big'] + df.loc['pod_straße_cargo_big','kosten_schnittstellen']
    
    # Carrier Small
    df.loc['carrier_straße_small', 'anschaffungskosten'] = (var['costs_carrier_street_small'] * var['ratio_carrier_normal_vehicle_small']
                                                     + df.loc['carrier_straße_small','kosten_schnittstellen'] )
    
    # Carrier Big
    df.loc['carrier_straße_big', 'anschaffungskosten'] = (var['costs_carrier_street_big'] * var['ratio_carrier_normal_vehicle_big'] 
                                                   + df.loc['carrier_straße_big','kosten_schnittstellen'] )
    
    # Carrier Small Cargo
    df.loc['carrier_straße_cargo_small', 'anschaffungskosten'] = df.loc['carrier_straße_small', 'anschaffungskosten']
    
    # Carrier Big Cargo
    df.loc['carrier_straße_cargo_big', 'anschaffungskosten'] = df.loc['carrier_straße_big', 'anschaffungskosten']
    
    df.loc[[x for x in df.index if 'carrier' in x], 'anschaffungskosten'] *= const['automatisierungsfaktor']
    
    
    def kalk_kosten(df, var):
        df = df.copy()
        
        df.loc[:, 'restwert'] = (var['restwert'] / 100) * df.loc[:, 'anschaffungskosten']
        p = var['kalk_zinsatz'] / 100
        a = var['nutzungsdauer']
        l = var['jahreskilometer']
        
        df.loc[:, 'kalk_kosten'] = (((df.loc[:, 'anschaffungskosten'] - df.loc[:, 'restwert']) * math.pow(1 + p, a)) 
                                    / ((math.pow(1 + p, a)) - 1) 
                                    + df.loc[:, 'restwert'] * p) 
        df.loc[:, 'kalk_kosten'] = df.loc[:, 'kalk_kosten'] / (l*a)
        return df
    
    
    def antrieb_kosten(df, var, allgemein, pod_df):
        df = df.copy()
        df_tmp = df.reindex([x for x in df.index if 'carrier' in x])
        pod_tmp = pod_df.copy()
        
        pod_series = np.where(pod_tmp.loc[(pods, 'is_elektro'),'pod'],
                              pod_tmp.loc[(pods, 'verbrauch'),'pod'] * allgemein['kosten_energie'],
                              pod_tmp.loc[(pods, 'verbrauch'),'pod'] * allgemein['kosten_diesel']
                             )
        
        dic = dict(zip([x for x in df.index if 'pod' in x], pod_series))
        pod_df = pd.DataFrame.from_dict(dic, columns=['pod'], orient='index')
        dic = dict(zip([x for x in df.index if 'pod' in x], [x for x in df.index if 'carrier' in x]))
        pod_df = (pod_df.rename(dic, level=0))
        
        output = df_tmp.merge(pod_df, left_index=True, right_index=True).assign(energie_kosten=lambda x: x['pod']).drop(columns='pod')
        
        df.loc[idx[[x for x in df.index if 'carrier' in x],:]] = output
        
        return df
    
    
    def reifen_kosten(df, var, allgemein):
        v_mittel = allgemein['v_mittel']
        
        if v_mittel <= 22:
            k_reifen = 0.15
        elif 22 < v_mittel <= 32:
            k_reifen = 0.15 - (v_mittel - 22) * 0.03
        else:
            k_reifen = 0.12
            
        df.loc[[x for x in df.index if 'carrier' in x], 'reifen_kosten'] = k_reifen
        
        return df
    
    
    def instandhaltungs_kosten(df, var, allgemein, pod_df):
        l = var['jahreskilometer']
        var_kosten_elektro = var['kosten_instandhaltung_elektro'] / l
        var_kosten_diesel = var['kosten_instandhaltung_diesel'] / l
        
        series = list(np.where(pod_df.loc[(pods, 'is_elektro'),'pod'], var_kosten_elektro, var_kosten_diesel))
        dic = dict(zip(df.index, series * 2))
        pod_df = pd.DataFrame.from_dict(dic, columns=['pod'], orient='index')
        output = df.merge(pod_df, left_index=True, right_index=True).assign(instandhaltung_kosten=lambda x: x['pod']).drop(columns='pod')
        df.loc[:, 'instandhaltung_kosten'] = output
        
        #if allgemein['is_elektro']:
        #    df.loc[:, 'instandhaltung_kosten'] = var['kosten_instandhaltung_elektro'] / l
        #else: 
        #    df.loc[:, 'instandhaltung_kosten'] = var['kosten_instandhaltung_diesel'] / l
        return df
    
    
    def overhead_kosten(df, var, allgemein):
        n = var['anzahl_fahrzeuge']
        l = var['jahreskilometer']
        k_overhead = 0.4 + (0.2/150) * n
        
        v_mittel = allgemein['v_mittel']
        
        if v_mittel <= 22:
            f_v = 1.3
        elif 22 < v_mittel <= 30:
            f_v = 1.3 - (0.5/12) * (v_mittel - 22)
        else:
            f_v = 0.7
        
        df.loc[[x for x in df.index if 'carrier' in x], 'overhead_kosten'] = k_overhead * f_v / l
        
        return df
    
    def versicherungs_kosten(df, var, allgemein):
        k_versicherung = var['versicherungskosten']
        l = var['jahreskilometer']
        
        df.loc[:, 'versicherung_kosten'] = k_versicherung /l
        
        return df

        
    df = kalk_kosten(df, var)
    
    df = antrieb_kosten(df, var, allgemein, pod_df)
    
    df = reifen_kosten(df, var, allgemein)
    
    df = instandhaltungs_kosten(df, var, allgemein, pod_df)
    
    df = versicherungs_kosten(df, var, allgemein)
    
    df = overhead_kosten(df, var, allgemein)
    
    df = df.round(2)
    
    gesamt_kosten = ['kalk_kosten',  # €/km
                    'energie_kosten',  # €/km
                    'instandhaltung_kosten',  # €/km
                    'versicherung_kosten',  # €/km
                    'reifen_kosten',  # €/km
                    'overhead_kosten'  # €/km
    ]  
    
    df.loc[:, 'kosten'] = df.loc[:,gesamt_kosten].sum(axis=1).round(2)
      
    for i in index:
        print('\n' + i)
        print('Anschaffungskosten [€]: \t \t  ' + str(df.loc[i, "anschaffungskosten"] ))
        print('Anteil Schnittstellen [%]:  \t \t  {}'.format(round(df.loc[i, "kosten_schnittstellen"] * 100 / df.loc[i, 'anschaffungskosten'] )))
        print('-----------------------------------------------------------')
        print('Kalkulatorische Kosten [€/km]: \t \t  {}'.format(df.loc[i,'kalk_kosten']))
        print('Energie Kosten [€/km]: \t \t \t  {}'.format(df.loc[i,'energie_kosten']))
        print('Reifen Kosten [€/km]: \t \t \t  {}'.format(df.loc[i,'reifen_kosten']))
        print('Instandhaltung Kosten [€/km]: \t \t  {}'.format(df.loc[i,'instandhaltung_kosten']))
        print('Overhead Kosten [€/km]: \t \t  {}'.format(df.loc[i,'overhead_kosten']))
        print('Versicherung Kosten [€/km]: \t \t  {}'.format(df.loc[i,'versicherung_kosten']))
        print('-----------------------------------------------------------')
        print('Gesamtkosten [€/km]: \t \t \t  {}'.format(df.loc[i, 'kosten']))
        
        if not 'carrier' in i:
            i_new = 'carrier_' + '_'.join(i.split('_')[1:])
            pod_df.loc[(i, 'kosten'), 'pod'] =  (df.loc[i, 'kosten'] + df.loc[i_new,gesamt_kosten].sum())/ pod_df.loc[(i, 'transportmenge'), 'pod']
            print('spez. Gesamtkosten [€/Pkm, €/Tkm]: \t  {}'.format(round(df.loc[i, 'kosten']/ pod_df.loc[(i, 'transportmenge'), 'pod'], 2))) 
        else:
            i_new = 'pod_' + '_'.join(i.split('_')[1:])
            print('spez. Gesamtkosten [€/Pkm, €/Tkm]: \t  {}'.format(round(df.loc[i, 'kosten']/ pod_df.loc[(i_new, 'transportmenge'), 'pod'], 2)))
            
            
    '''
    Berechnung Schiene
    '''
    
    s_entgelt = var['stationsentgelt']
    energiekosten = var['energiekosten'] * allgemein['energiekosten_entwicklung']
    reinigung = var['reinigung_und_instandhaltung']
    verwaltung_und_gewinn = var['verwaltung_und_gewinn']
    kapital_kosten = var['kapialkosten'] * var['ratio_kapital_kosten']
    ergebnis = sum([s_entgelt, energiekosten, reinigung, verwaltung_und_gewinn, kapital_kosten])
    pod_schiene = [x for x in pod_df.index.levels[0] if 'schiene' in x]
    dic = dict(zip(pod_schiene, [ergebnis] * (len(pod_schiene) + 1)))
    
    for k, v in dic.items():
        if 'cargo' in k:
            pod_name = 'pod_straße_' + '_'.join(k.split('_')[2:-1])
            if 'big' in k:
                pod_df.loc[(k, 'kosten'), 'pod'] = ((v * 2) / var['anzahl_pod_plaetze']) + df.loc[pod_name,'kosten']
            else:
                pod_df.loc[(k, 'kosten'), 'pod'] = (v / var['anzahl_pod_plaetze']) + df.loc[pod_name,'kosten']
            pod_df.loc[(k, 'kosten'), 'pod'] /=  pod_df.loc[(pod_name, 'transportmenge'), 'pod']
        else:
            pod_name = 'pod_straße_' + k.split('_')[-1]
            if 'big' in k:
                pod_df.loc[(k, 'kosten'), 'pod'] = ((v * 2) / var['anzahl_pod_plaetze']) + df.loc[pod_name,'kosten']
            else:
                pod_df.loc[(k, 'kosten'), 'pod'] = (v / var['anzahl_pod_plaetze'])+ df.loc[pod_name,'kosten'] 
            pod_df.loc[(k, 'kosten'), 'pod'] /=  pod_df.loc[(pod_name, 'transportmenge'), 'pod']
    
    
    print('-----------------------------------------------------------')
    print('\n' + 'Schiene')
    print('Gesamtkosten [€/km]: \t \t \t  {}'.format(round(ergebnis, 2)))
    print('spez. Gesamtkosten [€/Podplatzkm]: \t  {}'.format(round(ergebnis / var['anzahl_pod_plaetze'], 2)))
    
    return pod_df
    
    
    


    