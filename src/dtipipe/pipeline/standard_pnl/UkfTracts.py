from luigi import Parameter, IntParameter
import luigi.util

from plumbum import local

from dtipipe import ukf_tract_querier
from dtipipe import REPO_DIR
from dtipipe import util
from .BaseTask import BaseTask
from .WmparcInDwi import WmparcInDwi
from .Ukf import Ukf


DEFAULT_QUERY_FILE = REPO_DIR / 'scripts' / 'wmql-2.0.qry'


@luigi.util.inherits(WmparcInDwi)
@luigi.util.inherits(Ukf)
class UkfTracts(BaseTask):

    tract_querier_query_file = Parameter(default=DEFAULT_QUERY_FILE)
    num_proc_ukf_tract_querier = IntParameter()

    def requires(self):
        return dict(tractography=self.clone(Ukf),
                    atlas=self.clone(WmparcInDwi))

    def output(self):
        stem = local.path(self.tract_querier_query_file).stem
        return local.path(self.output_session_dir) / f'{self.output_basename}.tracts.{stem}'

    def run(self):
        ukf_tract_querier.ukf_tract_querier(ukf_vtk=self.input()['tractography'],
                                            atlas_file=self.input()['atlas']['wmparc_in_dwi'],
                                            query_file=self.tract_querier_query_file,
                                            output_dir=self.output(),
                                            num_proc=self.num_proc_ukf_tract_querier)

    def freeview_wmparc_in_dwi(self):
        self.requires()['atlas'].freeview()
