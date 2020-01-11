import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.core.display import HTML, display
from matplotlib.pyplot import figure

import helper
from import_dfs import Datenbank

warnings.filterwarnings('ignore')


class calculation():

    def __init__(self, db, szenario):
        self.szenario = szenario
        self.szenario_year = dict(
            klassisch=2017,
            trendszenario=2050,
            optimiert=2050,
            autonom=2050,
            pod=2050,
        )
        self.year = self.szenario_year[self.szenario]

        self.idx = pd.IndexSlice

        self.oev_list = ['bus', 'zug_nahverkehr',
                         'u_bahn', 'zug_fernverkehr', 'tram']
        # In der Literatur nur per Trip angegeben
        self.per_trip_costs = ["flugzeug", 'bus', 'tram', 'u_bahn']

        if self.szenario != 'pod':
            self.rf_pv_basis = db.rf_pv_basis.copy()
        else:
            self.rf_pv_basis = db.rf_pv_pod.copy()

        self.tech_data = db.technologiedaten.copy()
        self.df_rad = db.informationen_rad.copy()
        self.rf_pv_strecken = db.rf_pv_strecken.copy()
        self.cities = db.staedte.copy()
        self.bevoelkerungsverteilung = db.bevoelkerungsverteilung.copy()
        self.anpassungen = db.anpassungen_rf.copy(
        ).loc[self.idx[:, :], self.szenario.title()]

        self.unique_modes_fitted, self.unique_modes_dict = self.find_unique_modes()
        self.categorize = self.find_cats()

        self.tech_data, self.fitted_index_lvl_0 = self.fit_index(
            self.tech_data)  # anpassen der Indizes
        # Ausprobieren für Szenario Klassisch muss angepasst werden
        self.tech_data = pd.DataFrame(self.tech_data.loc[:, self.szenario])

    def find_unique_modes(self):
        unique_modes = self.tech_data.index.levels[0]
        unique_modes_fitted = helper.lower_and_underscores(unique_modes)
        unique_modes_dict = dict(zip(unique_modes, unique_modes_fitted))

        return unique_modes_fitted, unique_modes_dict

    def fit_index(self, df):

        fitted_index_lvl_0 = helper.lower_and_underscores(
            df.index.levels[0])  # modes werden angepasst
        df.index.set_levels(fitted_index_lvl_0, level=0,
                            inplace=True)  # Umbenennen der Kategorien

        return df, fitted_index_lvl_0

    def find_cats(self):
        # Kategorien, in denen die Bewertung vorgenommen wird
        categorize = self.tech_data.index.levels[1].to_list()
        categorize.remove('verfuegbarkeit')
        categorize.remove('auslastung')
        return categorize

    def run_calc(self):
        '''
        Emissionen bestimmen und aufaddieren.
        '''
        if self.szenario != 'pod':
            rf_pv_basis = self.rf_pv_basis.copy().drop(columns='bike_sharing')  # init
        else:
            rf_pv_basis = self.rf_pv_basis.copy()  # init
            rf_pv_basis = self.anpassungen_pod(rf_pv_basis)

        # display(HTML(rf_pv_basis.to_html()))

        rf_pv_basis = self.szenario_anpassungen(rf_pv_basis)
        # display(HTML(rf_pv_basis.to_html()))

        rf_pv_basis = self.calc_emissions_per_mode(rf_pv_basis)
        rf_pv_basis = self.sum_emissions(rf_pv_basis)
        # display(HTML(rf_pv_basis.to_html()))

        rf_pv_basis = self.add_explanation_cols(rf_pv_basis)
        # display(HTML(rf_pv_basis.to_html()))

        if self.szenario != 'pod':
            rf_pv_basis = self.zusammenfassen_oev(rf_pv_basis)

            rf_pv_basis = self.add_ratios_to_bike(rf_pv_basis)
            rf_pv_basis = self.sum_ratios_bike(rf_pv_basis)
        else:
            rf_pv_basis = self.change_pod_name(rf_pv_basis)

        rf_pv_basis = self.ratio_cities(rf_pv_basis)
        # display(HTML(rf_pv_basis.to_html()))

        ausgabe = self.style_ausgabe(rf_pv_basis)

        return rf_pv_basis, ausgabe

    def szenario_anpassungen(self, df):
        '''
        Passt die Szenarien über gegebene Werte an.
        '''
        rf_pv_basis = df.copy()
        anpassungen = self.anpassungen.copy()
        anpassungen, _ = self.fit_index(anpassungen)

        modes = self.unique_modes_fitted
        modes = [
            x for x in modes if x in df.columns and x in anpassungen.index.levels[0]]

        df = anpassungen

        ul = ['_'.join([x, 'wtime']) for x in modes]
        ul_2 = ['_'.join([x, 'ftime']) for x in modes]

        df_tmp = pd.DataFrame(0, index=rf_pv_basis.index, columns=ul+ul_2)
        rf_pv_basis = rf_pv_basis.merge(
            df_tmp, left_index=True, right_index=True)

        for mode in modes:
            rf_pv_basis.loc[:, mode] *= df.loc[mode, 'Length']
            rf_pv_basis.loc[:, f'{mode}_wtime'] = df.loc[mode, 'Wartezeit']
            rf_pv_basis.loc[:, f'{mode}_ftime'] = df.loc[mode, 'Fahrtzeit']

        rf_pv_basis.loc[:, 'length'] = rf_pv_basis.reindex(
            columns=modes).sum(axis=1)

        for mode in modes:
            rf_pv_basis.loc[:, f'{mode}_wtime'] *= (
                (rf_pv_basis.loc[:, mode] / rf_pv_basis.loc[:, 'length']))
            rf_pv_basis.loc[:, f'{mode}_ftime'] *= (
                (rf_pv_basis.loc[:, mode] / rf_pv_basis.loc[:, 'length']))

        # Multiplikation der Fahrzeit mit dem Gesamtfaktor und löchen der Hilfscols
        rf_pv_basis["fahrtzeit"] *= rf_pv_basis.loc[:, ul_2].sum(axis=1)
        rf_pv_basis = rf_pv_basis.drop(ul_2, axis=1)
        # Multiplikation Wartezeit mit Gesamtfaktor und löchen der Hilfscols
        rf_pv_basis["wartezeit"] *= rf_pv_basis.loc[:, ul].sum(axis=1)
        rf_pv_basis = rf_pv_basis.drop(ul, axis=1)
        # Zusammenfügen zur neuen Gesamtfahrzeit
        rf_pv_basis.loc[:, 'transferzeit'] = rf_pv_basis.reindex(
            ['wartezeit', 'fahrtzeit'], axis='columns').sum(axis=1)

        return rf_pv_basis

    def change_pod_name(self, rf_pv_basis):
        '''
        Ordnen Pods in die Gruppen Big und Small
        '''
        def f(x): return 'pod_big' if 'big' in x else 'pod_small'
        rf_pv_basis.loc[:, 'main_mode'] = rf_pv_basis.loc[:,
                                                          'main_mode'].map(f)
        return rf_pv_basis

    def calc_emissions_per_mode(self, rf_pv_basis):
        '''
        Berechnen der Emissionen je Mode.
        '''
        df = rf_pv_basis.copy()
        tech_data = self.tech_data.copy()

        for mode in self.fitted_index_lvl_0:
            for cat in self.categorize:
                if mode in df.columns.to_list() and not (cat == "kosten" and mode in self.per_trip_costs or cat == 'unfallrisiko'):  # Standardfall
                    df.loc[:, f'{mode}_{cat}'] = (
                        df.loc[:, mode] / 1000) * tech_data.loc[(mode, cat), :].values[0]
                elif mode in df.columns.to_list() and (cat == "kosten" and mode in self.per_trip_costs):  # Kosten werden per Trip berechnet
                    df.loc[:, f'{mode}_{cat}'] = df.apply(lambda x: tech_data.loc[(
                        mode, cat), :].values[0] if x.loc[mode] != 0 else 0, axis=1)
                elif mode in df.columns.to_list() and cat == 'unfallrisiko':  # Unfallrisiko ist auf 1 Mrd. km bezogen
                    df.loc[:, f'{mode}_{cat}'] = df.loc[:, mode] * \
                        (tech_data.loc[(mode, cat), :].values[0] /
                         1000000000000)  # Trillion

        return df

    def sum_emissions(self, df):
        '''
        Aufsummierend der Emissionene in neue Spalten.
        '''
        for cat in self.categorize:
            df.loc[:, f'{cat}'] = df.loc[:, [
                f'{mode}_{cat}' for mode in self.unique_modes_fitted]].sum(axis=1)
        return df

    def add_explanation_cols(self, rf_pv_basis):
        '''
        Nimmt die Streckendaten und fügt drei Spalten (main_mode, num_modes und only_mode) hinzu.
        '''

        rf_pv_basis.loc[:, 'main_mode'] = rf_pv_basis.loc[:, self.unique_modes_fitted].idxmax(
            axis=1)  # find mode with highest length percentage
        rf_pv_basis.loc[:, 'num_modes'] = (rf_pv_basis.loc[:, self.unique_modes_fitted] > 0).sum(
            axis=1)   # find number of modes in row
        rf_pv_basis.loc[:, 'only_mode'] = np.where(
            rf_pv_basis['num_modes'] == 1, True, False)  # if num modes == 1 -> only_mode = True

        return rf_pv_basis

    def style_ausgabe(self, rf_pv_basis):
        '''
        Vereinheitetlicht die Ausgabe der Datenframes hinsichtlich der Nachkommastellen. Rückabe ist ein vereinfachter DataFrame und einmal der vollständige.
        '''

        df = rf_pv_basis.copy()

        df.loc[:, ['transferzeit', 'wartezeit', 'fahrtzeit', 'length']] = df.loc[:, [
            'transferzeit', 'wartezeit', 'fahrtzeit', 'length']].round(0).astype(int)
        df.loc[:, 'kosten'] = df.loc[:, 'kosten'].round(2)
        df.loc[:, ['energieverbrauch', 'thg', 'nox', 'pm']] = df.loc[:,
                                                                     ['energieverbrauch', 'thg', 'nox', 'pm']].round(4)

        # TODO: Rename Columns here with units

        ausgabe = df.loc[:, ['transferzeit', 'fahrtzeit', 'wartezeit', 'length',
                             'thg', 'nox', 'pm', 'energieverbrauch', 'kosten', 'unfallrisiko']]

        ausgabe = ausgabe.rename(index=str.title, level=0)
        ausgabe = ausgabe.rename(columns=str.title)
        # Umwandeln der Zeiten und umwandeln in bessere Einheiten
        ausgabe = ausgabe.assign(
            Fahrtzeit=pd.to_datetime(
                ausgabe.Fahrtzeit, unit='m').dt.strftime('%H:%M'),
            Transferzeit=pd.to_datetime(
                ausgabe.Transferzeit, unit='m').dt.strftime('%H:%M'),
            Wartezeit=pd.to_datetime(
                ausgabe.Wartezeit, unit='m').dt.strftime('%H:%M'),
            Length=lambda x: x.Length / 1000,
            THG=lambda x: x.Thg / 1000,
        ).drop(columns=['Thg']).reindex(columns=['Transferzeit', 'Fahrtzeit', 'Wartezeit', 'Length', 'THG', 'Nox', 'Pm', 'Energieverbrauch', 'Kosten', 'Unfallrisiko'])

        ausgabe = ausgabe.rename(columns={
            'Length': 'Länge [km]',
            'Transferzeit': 'Transferzeit [std:min]',
            'Wartezeit': 'Wartezeit [std:min]',
            'Fahrtzeit': 'Fahrtzeit [std:min]',
            'Kosten': 'Kosten [€]',
            'Unfallrisiko': 'Unfallrsikio [*]',
            'Energieverbrauch': 'Energieverbrauch [MJ]',
            'THG': 'THG [kg CO$_2$-eq]',
            'Nox': 'NOX [g]',
            'Pm': 'PM [g]'
        })

        # ausgabe = ausgabe.rename(index={
        #    'UK': 'Urban-Kurzstrecke',
        #    'UL': 'Urban-Langstrecke',
        #    'I': 'Intercity',
        #    'L': 'Langstrecke'
        # }, level=1)

        ausgabe = ausgabe.rename(index={
            'Miv': 'MIV',
            'Oev': 'ÖV',
            'Rad': 'Fahrrad',
            'Zu_Fuss': 'zu Fuß',
            'Pod_Big': ' Pod Big',
            'Pod_Small': 'Pod Small'
        }, level=0)

        ausgabe = ausgabe.reset_index().rename(columns={
            'main_mode': 'Verkehrsmittel',
            'strecken_typ': 'Streckentyp'
        }).set_index(['Verkehrsmittel', 'Streckentyp']).reindex(index=['UK', 'UL', 'I', 'L'], level='Streckentyp')

        return ausgabe

    def zusammenfassen_oev(self, rf_pv_basis):
        # Zusammenfassen von oev
        rf_pv_basis.loc[:, 'oev'] = rf_pv_basis.reindex(
            self.oev_list, axis='columns').sum(axis=1)
        zipped = dict(zip(self.oev_list, ['oev'] * 5))
        rf_pv_basis.loc[:, 'main_mode'] = rf_pv_basis.apply(
            lambda row: zipped[row['main_mode']] if row['main_mode'] in self.oev_list else row['main_mode'], axis=1)

        return rf_pv_basis

    def add_ratios_to_bike(self, rf_pv_basis):
        '''
        Fügt die Verhältnisse der Fahrräder hinzu
        '''
        df = rf_pv_basis.copy()

        anteil_ebike_2017 = self.df_rad.loc['E-Bike',
                                            (2017, 'Anzahl')] / self.df_rad.loc['Rad_insgesamt', (2017, 'Anzahl')]
        anteil_ebike_2050 = self.df_rad.loc['E-Bike',
                                            (2050, 'Anzahl')] / self.df_rad.loc['Rad_insgesamt', (2050, 'Anzahl')]

        cols = df.select_dtypes(
            include=['number']).columns.drop('name_verbindung')

        if self.year == 2017:
            df.loc[df.loc[:, 'fahrrad'] > 0, cols] *= (1 - anteil_ebike_2017)
            df.loc[df.loc[:, 'e_bike'] > 0, cols] *= anteil_ebike_2017
        else:
            df.loc[df.loc[:, 'fahrrad'] > 0, cols] *= (1 - anteil_ebike_2050)
            df.loc[df.loc[:, 'e_bike'] > 0, cols] *= anteil_ebike_2050

        return df

    def sum_ratios_bike(self, rf_pv_basis):
        '''
        Zusammenfassen Fahrrad und E_bike
        '''
        df = rf_pv_basis.copy()

        delet_cols = list()

        for c in self.categorize:
            zipped = [f'e_bike_{c}', f'fahrrad_{c}']
            df.loc[:, f'rad_{c}'] = df.reindex(
                zipped, axis='columns').sum(axis=1)
            delet_cols.extend(zipped)

        df.loc[:, 'rad'] = df.reindex(
            ['e_bike', 'fahrrad'], axis='columns').sum(axis=1)
        df = df.drop(columns=delet_cols + ['e_bike', 'fahrrad'])

        df_w_rad = df.loc[df.loc[:, 'rad'] > 0]

        grouped = df_w_rad.groupby('name_verbindung')

        cols = df.select_dtypes(
            include=['number']).columns.drop('name_verbindung')
        no_cols = df.select_dtypes(
            exclude=['number']).columns.insert(0, 'name_verbindung')

        df_w_rad = grouped[cols].sum().merge(df.loc[df.loc[:, 'rad'] > 0, no_cols],
                                             left_index=True, right_on='name_verbindung').drop_duplicates('name_verbindung')
        df_w_rad.loc[:, 'main_mode'] = np.where(
            df_w_rad.loc[:, 'main_mode'] == 'fahrrad', 'rad', df_w_rad.loc[:, 'main_mode'])
        df = df.loc[df.loc[:, 'rad'] == 0].append(df_w_rad, sort=False).sort_values(
            by=['name_verbindung']).set_index('name_verbindung')

        return df

    def ratio_cities(self, rf_pv_basis):
        '''
        Rechnet die verschiedenen Aufteilungen der Städte mit ein!
        '''
        df = rf_pv_basis.copy()

        cities = self.cities.drop(columns=['stadt_größe', 'stadt_name'])

        rf_pv_routes = (self.rf_pv_strecken.drop(columns=['strecken_typ', 'luftlinie', 'startpunkt', 'endpunkt', 'stadt_start', 'stadt_ende'])
                        .assign(stadt_id_ende=lambda x: x['stadt_id_ende'].astype(int),
                                stadt_id_start=lambda x: x['stadt_id_start'].astype(int)))

        df = (df.merge(rf_pv_routes, left_on='name_verbindung', right_index=True)
              .merge(cities, left_on='stadt_id_start', right_on='stadt_id', suffixes=(False, '_start'))
              .merge(cities, left_on='stadt_id_ende', right_on='stadt_id', suffixes=('_start', '_ende')))
        df = df.drop(columns=['stadt_id_start', 'stadt_id_ende']).reset_index().rename(
            columns={'index': 'name_verbindung'})

        #cols = df.select_dtypes(include=['number']).columns.drop('name_verbindung')

        df.loc[df.loc[:, 'stadt_typ_start'] == df.loc[:, 'stadt_typ_ende'],
               'stadt_typ'] = df.loc[:, 'stadt_typ_start']
        df_tmp = df.loc[df.loc[:, 'stadt_typ'].isnull()]
        df_tmp.loc[df_tmp.loc[:, 'stadt_typ'] != df_tmp.loc[:, 'stadt_typ'],
                   'stadt_typ'] = df_tmp.loc[df_tmp.loc[:, 'stadt_typ'] != df_tmp.loc[:, 'stadt_typ'], 'stadt_typ_start']
        df = df.append(df_tmp, ignore_index=True)
        df.loc[df.loc[:, 'stadt_typ'] != df.loc[:, 'stadt_typ'],
               'stadt_typ'] = df.loc[df.loc[:, 'stadt_typ'] != df.loc[:, 'stadt_typ'], 'stadt_typ_ende']
        df = df.drop(columns=['stadt_typ_start', 'stadt_typ_ende'])

        grouped = df.groupby(['strecken_typ', 'stadt_typ', 'main_mode'])
        #grouped = grouped[cols].median()
        grouped = grouped.mean().drop(columns=['name_verbindung'])

        # for stadt in self.bevoelkerungsverteilung.loc['Klassisch',:].T.index:
        #    grouped.loc[idx['I', stadt, :]] *= (self.bevoelkerungsverteilung.loc[self.szenario.title(),stadt])

        grouped = grouped.reset_index().groupby(
            ['main_mode', 'strecken_typ']).mean().drop(columns=['num_modes'])

        return grouped

    def anpassungen_pod(self, rf_pv_basis):
        df = rf_pv_basis.copy()

        def f(x): return x.lower().replace(
            ' ', '_') if isinstance(x, str) else x
        df.loc[:, [f'mode_{i}' for i in range(1, 7)]] = df.loc[:, [
            f'mode_{i}' for i in range(1, 7)]].applymap(f)

        unique_modes_fitted = (
            pd.unique(df.loc[:, [f'mode_{i}' for i in range(1, 7)]].values.ravel()))

        df_new = pd.DataFrame(0, index=df.index, columns=unique_modes_fitted)

        result = pd.concat([df, df_new], axis=1, sort=False)

        def transform_df(row):
            '''
            Nimmt eine row und schreit die Gesamtkilometer je Verkehrmittel in das zur Spalte gehörige Feld.
            '''
            for i in range(1, 7):
                mode = row.loc[f'mode_{i}']
                if mode not in [np.nan, np.NaN, 'nan']:
                    row.loc[mode] += row.loc[f'mode_length_{i}']
                else:
                    continue
            return row

        result = result.apply(lambda row: transform_df(row), axis=1)

        result = result.drop(columns=[f'mode_{i}' for i in range(
            1, 7)] + [f'mode_length_{i}' for i in range(1, 7)] + [np.nan])

        df = result.copy()
        df_tmp = result.copy()

        df.loc[:, 'pod_straße_small'] = df.loc[:, 'pod_straße']
        df_tmp.loc[:, 'pod_straße_big'] = df.loc[:, 'pod_straße']

        df.loc[:, 'pod_schiene_nah_small'] = df.loc[:, 'pod_schiene_nah']
        df_tmp.loc[:, 'pod_schiene_nah_big'] = df.loc[:, 'pod_schiene_nah']

        df.loc[:, 'pod_schiene_fern_small'] = df.loc[:, 'pod_schiene_fern']
        df_tmp.loc[:, 'pod_schiene_fern_big'] = df.loc[:, 'pod_schiene_fern']

        cols = ['pod_straße_big', 'pod_schiene_nah_big', 'pod_schiene_fern_big']

        df = df.drop(columns=['pod_straße', 'pod_schiene_nah'])
        df_tmp = df_tmp.drop(columns=['pod_straße', 'pod_schiene_nah'])

        df = df.append(df_tmp, ignore_index=True).fillna(
            0).sort_values('name_verbindung')

        return df     




class complete_calc():

    def __init__(self, db):
        self.db = db
        self.run_entire_calc()
        self.szenarios = ['klassisch', 'trendszenario',
                          'autonom', 'optimiert', 'pod']

    def run_entire_calc(self):
        for s in ['klassisch', 'trendszenario', 'autonom', 'optimiert', 'pod']:
            calc = calculation(self.db, s)
            df, ausgabe = calc.run_calc()
            setattr(self, s, df)
            setattr(self, f'{s}_ausgabe', ausgabe)
            
        scenarios = ['Klassisch', 'Trendszenario', 'Optimiert', 'Autonom']
        for scenario in scenarios:
            df = getattr(self, f'{scenario.lower()}_ausgabe').reset_index().set_index(['Streckentyp', 'Verkehrsmittel'])
            df.columns = pd.MultiIndex.from_product([[scenario], df.columns])
            if scenario == 'Klassisch':
                tmp = df
            else:
                tmp = tmp.merge(df, left_index=True, right_index=True)
                
        tmp = tmp.stack()
        tmp.index = tmp.index.set_names('Kategorien', level=2)
        
        df = self.pod_ausgabe.reset_index()
        df = pd.DataFrame(df.set_index(['Streckentyp','Verkehrsmittel']).stack()).rename(columns={0: 'Pod'})
        df.index = df.index.set_names('Kategorien', level=2)
        output = tmp.append(df).fillna(0)
        output = output.reindex(columns=scenarios + ['Pod'])
        self.vergleich = output

    def print_all(self):
        for s in ['klassisch', 'trendszenario', 'autonom', 'optimiert', 'pod']:
            display(HTML(f'<h2>Szenario: {s.title()}</h1>'))
            display(HTML(getattr(self, f'{s}_ausgabe').to_html()))
