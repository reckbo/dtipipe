import logging
import json
import toolz

import pytest
import coloredlogs
from plumbum import local, cli
import nibabel as nib

from . import nifti2nhdr
from . import TEST_DATA


log = logging.getLogger(__name__)

UKF_DEFAULT_PARAMS = {'numTensor': 2,
                      'stoppingFA': 0.15,
                      'seedingThreshold': 0.18,
                      'Qm': 0.001,
                      'Ql': 70,
                      'Rs': 0.015,
                      'stepLength': 0.3,
                      'recordLength': 1.7,
                      'stoppingThreshold': 0.1,
                      'seedsPerVoxel': 10}


def ukf(dwi_file, dwi_mask_file, output_vtk, ukftractography_bin='UKFTractography', **ukf_params):
    """
    Run UKFTractography on DWI and mask in NIFTI format.
    """

    with local.tempdir() as tmpdir:
        dwi_short = tmpdir / 'dwi_short.nii.gz'
        dwi_mask_short = tmpdir / 'mask_short.nii.gz'

        dwi_nrrd = tmpdir / 'dwi.nhdr'
        dwi_mask_nrrd = tmpdir / 'dwimask.nhdr'

        log.info('Typecast the DWI and mask to short (int16)')
        for (input_file, output_file) in [(dwi_file, dwi_short), (dwi_mask_file, dwi_mask_short)]:
            img = nib.load(str(input_file))
            nib.Nifti1Image(img.get_data().astype('int16'), img.affine, img.header) \
                .to_filename(output_file)

        log.info('Convert the DWI and mask to nrrd')
        nifti2nhdr.nifti2nhdr(dwi_short,
                              dwi_file.with_suffix('.bval', depth=2),
                              dwi_file.with_suffix('.bvec', depth=2),
                              dwi_nrrd)
        nifti2nhdr.nifti2nhdr(dwi_mask_short, None, None, dwi_mask_nrrd)

        ukf_params = {**UKF_DEFAULT_PARAMS, **ukf_params}
        ukf_params = toolz.concat([[f'--{param}', val] for (param, val) in ukf_params.items()])

        log.info('Run UKF tractography')
        UKFTractography = local[ukftractography_bin]
        UKFTractography('--dwiFile', dwi_nrrd,
                        '--maskFile', dwi_mask_nrrd,
                        '--seedsFile', dwi_mask_nrrd,
                        '--tracts', output_vtk,
                        '--recordTensors',
                        *ukf_params)


@pytest.mark.slow
def test_ukf(ukftractography_bin):
    input_dwi = TEST_DATA / 'dwi_eddy.nii.gz'
    input_mask = TEST_DATA / 'dwi_mask.nii.gz'
    # expected_output = TEST_DATA / 'dwi_tracts.vtk'
    with local.tempdir() as tmpdir:
        tmpdir = local.path('/tmp/ukf')
        output = tmpdir / 'tracts.vtk'
        ukf(input_dwi, input_mask, output, ukftractography_bin=ukftractography_bin)


class Cli(cli.Application):

    __doc__ = ukf.__doc__

    dwi_file = cli.SwitchAttr(
        ['--dwi'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='DWI in NIFTI format')

    dwi_mask_file = cli.SwitchAttr(
        ['--dwi-mask'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='DWI mask in NIFTI format')

    output_vtk = cli.SwitchAttr(
        ['-o', '--output'],
        argtype=cli.NonexistentPath,
        mandatory=True,
        help='Output vtk file')

    ukf_bin = cli.SwitchAttr(
        ['--ukf-bin'],
        argtype=str,
        default='UKFTractography',
        help='Path to the UKFTractography binary')

    ukf_params = cli.SwitchAttr(
        ['--params'],
        argtype=str,
        help="JSON dictionary of parameters for UKF, e.g. '{arg1:val1, arg2:val2}")

    log_level = cli.SwitchAttr(
        ['--log-level'],
        argtype=cli.Set("CRITICAL", "ERROR", "WARNING",
                        "INFO", "DEBUG", "NOTSET", case_sensitive=False),
        default='INFO',
        help='Python log level')

    def main(self):
        coloredlogs.install(level=self.log_level)
        ukf_params = json.loads(self.ukf_params)
        ukf(dwi_file=self.dwi_file,
            dwi_mask_file=self.dwi_mask_file,
            output_vtk=self.output_vtk,
            ukf_params=ukf_params)
