import matplotlib.pyplot as plt
import pandas as pd
import ipywidgets as widgets
import numpy as np
from IPython.core.display import HTML, display
import seaborn as sns

sns.set()

# Save a palette to a variable:
palette = sns.color_palette("hls", 5)

# Use palplot and pass in the variable:
sns.palplot(palette)


class Display_DFs():
    
    def __init__(self, s):
        self.s = s
        self.idx = pd.IndexSlice
        
        self.display_dfs()
        
    def build_tabs(self, name, tabs, typ='tab'):
        num = len(tabs)
        for i in range(0,num):
            setattr(self, f'{name}{i}', widgets.Output())
        
        if typ == 'tab':
            self.tab = widgets.Tab(children = [getattr(self, f'{name}{i}') for i in range(0,num)])
        
            for x,y in zip(range(0,num), tabs):
                self.tab.set_title(x ,y.title())
            display(self.tab)
        else:
            self.accordion = widgets.Accordion(children= [getattr(self, f'{name}{i}') for i in range(0,num)])
            
            for x,y in zip(range(0,num), tabs):
                self.accordion.set_title(x,y.title())
            self.accordion.selected_index = None
            display(self.accordion)
        
    def display_dfs(self):
        s = self.s
        name = 'out'
        self.build_tabs(name, ['Vergleich'] + s.szenarios)
        
        with getattr(self, f'{name}{0}'):
            display(HTML('<h3>Vergleich in den Dimensionen</h3'))
            self.dispaly_comprehension()
        
        for i, szenario in enumerate(s.szenarios):
            with getattr(self, f'{name}{i+1}'):
                display(HTML(f'<h2>Übersichtstabelle</h2>'))
                display(HTML(getattr(s, f'{szenario}_ausgabe').to_html()))
                display(HTML(f'<h2>Dimensionen</h2>'))
                self.display_plots(szenario)
                
    def display_plots(self, szenario):
        idx = self.idx
        s = self.s

        name = 'dout'
        tabs = [
            'Allgemein',
            'Ökonomie',
            'Ökologie',
            'Soziales'
        ]
        n_streckentyp = {
            'UK': 'Urban-Kurzstrecke',
            'UL': 'Urban-Langstrecke',
            'I': 'Intercity',
            'L': 'Langstrecke'
        }
        
        self.build_tabs(name, tabs, typ='acc')
        
        for i, dim in enumerate(tabs):
            with getattr(self, f'{name}{i}'):
                for streckentyp in ['UK', 'UL', 'I', 'L']:
                    display(HTML(f'<h4>{n_streckentyp[f"{streckentyp}"]}</h4>'))
                    df = getattr(s, f'{szenario}_ausgabe').loc[idx[:,streckentyp], :]
                    df = df.reset_index()
                    
                    if dim == 'Ökonomie':
                        f, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(10,4))
                        sns.barplot(x='Verkehrsmittel', y='Kosten [€]', data=df, ax=ax1)
                        sns.barplot(x='Verkehrsmittel', y="Unfallrsikio [*]", data=df, ax=ax2)
                        ax1.set_title('Kosten [€]')
                        ax2.set_title('Unfallrsikio')

                        plt.subplots_adjust(wspace=0.3)
                    elif dim == 'Allgemein':
                        f, ax1 = plt.subplots(nrows=1, ncols=1, figsize=(6,4))
                        sns.barplot(x='Verkehrsmittel', y='Länge [km]', data=df, ax=ax1)
                        ax1.set_title('Länge [km]')
                        
                    elif dim == 'Ökologie':
                        f, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(10,4))
                        sns.barplot(x='Verkehrsmittel', y='THG [kg CO$_2$-eq]', data=df, ax=ax1)
                        sns.barplot(x='Verkehrsmittel', y='NOX [g]', data=df, ax=ax2)
                        f, (ax3, ax4) = plt.subplots(nrows=1, ncols=2, figsize=(10,4))
                        sns.barplot(x='Verkehrsmittel', y='PM [g]', data=df, ax=ax3)
                        sns.barplot(x='Verkehrsmittel', y='Energieverbrauch [MJ]', data=df, ax=ax4)
                        ax1.set_title('THG [kg CO$_2$-eq]')
                        ax2.set_title('NOX [g]')
                        ax3.set_title('PM [g]')
                        ax4.set_title('Energieverbrauch [MJ]')
                    
                    elif dim == 'Soziales':
                        f, (ax1, ax2,ax3) = plt.subplots(nrows=1, ncols=3, figsize=(15,4))
                        
                        cols = {
                            'Transferzeit [std:min]': 'Transferzeit [min]',
                            'Wartezeit [std:min]': 'Wartezeit [min]',
                            'Fahrtzeit [std:min]': 'Fahrtzeit [min]'
                        }
                        for p in cols.keys():
                            df.loc[:,p] = pd.to_datetime(df[p]).dt.strftime('%H:%M:%S')
                            df.loc[:,p] = (pd.to_timedelta(df[p]).dt.total_seconds() / 60)
                        df = df.rename(columns=cols)
                        
                        sns.barplot(x='Verkehrsmittel', y='Transferzeit [min]', data=df, ax=ax1)
                        sns.barplot(x='Verkehrsmittel', y='Wartezeit [min]', data=df, ax=ax3)
                        sns.barplot(x='Verkehrsmittel', y='Fahrtzeit [min]', data=df, ax=ax2)
                        ax1.set_title('Transferzeit [min]')
                        ax3.set_title('Wartezeit [min]')
                        ax2.set_title('Fahrtzeit [min]')
                    
                    plt.show()

    def dispaly_comprehension(self):
        name = 'fout'
        tabs = [
            'Allgemein',
            'Ökonomie',
            'Ökologie',
            'Soziales'
        ]
        n_streckentyp = {
            'UK': 'Urban-Kurzstrecke',
            'UL': 'Urban-Langstrecke',
            'I': 'Intercity',
            'L': 'Langstrecke'
        }
        self.build_tabs(name, tabs, typ='acc')
        df = self.s.vergleich
        grouped = df.groupby(['Streckentyp', 'Kategorien'])

        def build_plot(cat, streckentyp, fig, ax):
            
            for i, c in cat.items():
                df_tmp = pd.DataFrame(grouped.get_group((streckentyp, c)).stack(), columns=[c])
                df_tmp = df_tmp.reset_index().rename(columns={'level_3': 'Szenarien'})

                if 'zeit' in c:
                    cols = {
                        'Transferzeit [std:min]': 'Transferzeit [min]',
                        'Wartezeit [std:min]': 'Wartezeit [min]',
                        'Fahrtzeit [std:min]': 'Fahrtzeit [min]'
                    }
                    for p in cols.keys():
                        if p in df_tmp.columns:
                            df_tmp.loc[:,p] = pd.to_datetime(df_tmp[p]).dt.strftime('%H:%M:%S')
                            df_tmp.loc[:,p] = (pd.to_timedelta(df_tmp[p]).dt.total_seconds() / 60)
                    df_tmp = df_tmp.rename(columns=cols)
                    c = cols[c]

                if len(cat.keys()) == 1:
                    g = sns.barplot(x='Verkehrsmittel', y=c, hue='Szenarien', data=df_tmp, ax=ax)
                    box = g.get_position()
                    g.set_position([box.x0, box.y0 + box.height * 0.1,
                    box.width, box.height * 0.9]) # resize position

                    # Put a legend to the right side
                    legend = ax.legend(bbox_to_anchor=(0,-0.38,1,0.1), loc="lower left",
                                        borderaxespad=0, mode='expand', ncol=3)
                else:
                    g = sns.barplot(x='Verkehrsmittel', y=c, hue='Szenarien', data=df_tmp, ax=ax[i])
                    legend = ax[i].legend(bbox_to_anchor=(0,-0.38,1,0.1), loc="lower left",
                                        borderaxespad=0, mode='expand', ncol=3)


        for i, dim in enumerate(tabs):
            with getattr(self, f'{name}{i}'):
                for streckentyp in ['UK', 'UL', 'I', 'L']:
                    display(HTML(f'<h4>{n_streckentyp[f"{streckentyp}"]}</h4>'))

                    if dim == 'Allgemein':
                        f, ax = plt.subplots(nrows=1, ncols=1, figsize=(6,4))
                        cat = {
                            0: 'Länge [km]'
                        }
                        build_plot(cat, streckentyp, f, ax)
                    elif dim == 'Ökonomie':
                        f, ax = plt.subplots(nrows=1, ncols=2, figsize=(12,4))
                        cat = {
                            0: 'Kosten [€]',
                            1: 'Unfallrsikio [*]'
                        }
                        build_plot(cat, streckentyp, f, ax)
                    elif dim == 'Soziales':
                        f, ax = plt.subplots(nrows=1, ncols=3, figsize=(18,4))

                        cat = {
                            0: 'Transferzeit [std:min]',
                            1: 'Fahrtzeit [std:min]',
                            2: 'Wartezeit [std:min]'
                        }
                        build_plot(cat, streckentyp, f, ax)
                    else:
                        f, ax = plt.subplots(nrows=1, ncols=2, figsize=(12,4))
                        cat = {
                            0: 'Energieverbrauch [MJ]',
                            1: 'THG [kg CO$_2$-eq]'
                        }
                        build_plot(cat, streckentyp, f, ax)
                        f, ax = plt.subplots(nrows=1, ncols=2, figsize=(12,4))
                        cat = {
                            0: 'NOX [g]',
                            1: 'PM [g]'
                        }
                        build_plot(cat, streckentyp, f, ax)

                    plt.show()