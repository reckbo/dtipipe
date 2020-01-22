import os
from luigi import Parameter, IntParameter
import luigi.util

from plumbum import local

from dtipipe.measuretracts import measureTractsFunctions
from .BaseTask import BaseTask
from .TractQuerier import TractQuerier


@luigi.util.requires(TractQuerier)
class TractMeasures(BaseTask):

    def output(self):
        return local.path(str(self.input()) + '.csv')

    def run(self):
        vtks = self.input() // '*.vtk'
        measureTractsFunctions.printToCSV(vtks, self.output().__str__())

