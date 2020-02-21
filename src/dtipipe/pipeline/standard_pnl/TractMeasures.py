import luigi.util
import pandas as pd

from plumbum import local

from dtipipe.measuretracts import measureTractsFunctions
from ..BaseTask import BaseTask
from .TractQuerier import TractQuerier


@luigi.util.requires(TractQuerier)
class TractMeasures(BaseTask):

    def output(self):
        return local.path(str(self.input()) + '.csv')

    def run(self):
        vtks = self.input() // '*.vtk'
        measureTractsFunctions.printToCSV([str(vtk) for vtk in vtks], self.output().__str__())

    def read(self):
        df = pd.read_csv(str(self.output()))
        df[['tract_type', 'tract_hemi']] = df.tract.str.split('.', expand=True)
        return df.sort_values(by='tract').set_index('tract')

    def read_tract_measure(self, tract_type, tract_measure):
        left_key = f'{tract_type}_{tract_measure}_left'
        right_key = f'{tract_type}_{tract_measure}_right'
        result = {}
        result[left_key] = None
        result[right_key] = None
        if not self.complete():
            return result
        try:
            df = self.read()
            result = df.loc[tract_type, tract_measure].to_dict()
            result[left_key] = result.pop('left', None)
            result[right_key] = result.pop('right', None)
        except KeyError:
            pass
        return result
