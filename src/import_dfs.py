import pandas as pd
import configparser
import h5py
import tables

class Datenbank():

    def __init__(self):
        self.path = "../data/200107_data.h5"
        with h5py.File(self.path) as f:
            self.h5_keys = [k for k in f.keys()]
        print(self.h5_keys)
        self.dfs = self.load_hdf()
        for k, v in self.dfs.items():
            setattr(self, k.lower(), v)
        
    
    def load_hdf(self):
        dfs = dict()
        for name in self.h5_keys:
            if not name == 'verbesserungsfaktoren':
                try:
                    dfs[name] = pd.read_hdf(self.path, key=name, mode='r')
                except Exception as e:
                    print(e)
        return dfs

    
    def save_to_hdf(self):
        for name in self.dfs.keys():
            self._save(name)
            
        
    def _save(self, name):
        tables.file._open_files.close_all()
        df = getattr(self, name.lower())
        if isinstance(df, pd.DataFrame):
            try:
                df.to_hdf(self.path, format='table', key=name.lower(), mode= 'a')
                print(f'{name} - saved')
            except Exception as e:
                print(f'{name} - Not saved')
                print(e)

            
def main():
    return Datenbank()


if __name__ == "__main__":
    main()