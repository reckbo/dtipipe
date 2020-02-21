import logging

import luigi.util
from luigi import IntParameter, Parameter, FloatParameter
from plumbum import local

from ..BaseTask import BaseTask
from ..standard_pnl import DwiBetMask
from .Dti import Dti


@luigi.util.inherits(Dti)
class Tracks(BaseTask):

    dwi_bet_mask_threshold = FloatParameter()
    angular_threshold = IntParameter()
    filter_track_length = IntParameter()
    fsldir = Parameter()

    def requires(self):
        return dict(dwi_bet_mask=self.clone(DwiBetMask),
                    dti=self.clone(Dti))

    def output(self):
        return local.path(self.requires()['dti'].output_prefix() + f'_{self.angular_threshold}.trk')

    def run(self):
        log = logging.getLogger('luigi-interface')
        dti_tracker = local[self.dtk_dir + '/dti_tracker']
        spline_filter = local[self.dtk_dir + '/spline_filter']
        input_prefix = self.requires()['dti'].output_prefix()
        with local.tempdir() as tmpdir:
            tmp_tracks = tmpdir / 'tracks.trk'
            log.info('Compute tracks from DTI')
            cmd = dti_tracker[input_prefix,
                              tmp_tracks,
                              '-at', self.angular_threshold,
                              '-m', self.input()['dwi_bet_mask'],
                              '-it', 'nii.gz']
            log.info(f'Running: {cmd}')
            cmd()
            log.info('Filter tracks by length')
            cmd = spline_filter[tmp_tracks,
                                self.filter_track_length,
                                self.output()]
            log.info(f'Running: {cmd}')
            cmd()
