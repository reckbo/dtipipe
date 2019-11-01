import logging
from multiprocessing import Pool

import coloredlogs
from plumbum import cli, local

from . import activate_tensors
from . import TEST_DATA


log = logging.getLogger(__name__)


DEFAULT_NUM_PROC = 10


def _activate_tensors(vtk_file):
    new_vtk_file = vtk_file.dirname / (vtk_file.stem[2:] + ''.join(vtk_file.suffixes))
    log.info(f'Process {vtk_file} -> {new_vtk_file}')
    activate_tensors.activate_tensors(vtk_file, new_vtk_file)
    vtk_file.delete()


def ukf_tract_querier(ukf_vtk, atlas_file, query_file, output_dir, num_proc=DEFAULT_NUM_PROC):
    """
    Wrapper around tract_querier that first preprocesses the input tractography file
    before calling tract_querier.

    The following two preprocessing steps are performed:
      1. Short tracts are removed
      2. nan's and inf's are replaced by 0's and large finite numbers respectively.
    """

    ukf_vtk = local.path(ukf_vtk)
    atlas_file = local.path(atlas_file)
    query_file = local.path(query_file)
    output_dir = local.path(output_dir)

    with local.tempdir() as tmpdir:

        pruned_ukf_vtk = tmpdir / 'pruned_ukf.vtk'

        log.info(f'Remove short tracts from the tractography file (Make {pruned_ukf_vtk})')
        r = local['tract_math'].run([ukf_vtk, 'tract_remove_short_tracts', '2', pruned_ukf_vtk])
        log.debug(f'tract_math output: {r}')
        if not pruned_ukf_vtk.exists():
            raise Exception(f'tract_math failed to make {pruned_ukf_vtk}\n'
                            f'tract_math output: {r}')

        log.info(f'Run tract_querier (Make {output_dir}/*.vtk)')
        output_dir.mkdir()
        local['tract_querier'].run(['-t', pruned_ukf_vtk,
                                    '-a', atlas_file,
                                    '-q', query_file,
                                    '-o', output_dir / '_'])

        log.info(f"Update the tensor data format in each output vtk and replace nan's with 0 "
                 "and inf's with large finite numbers")
        pool = Pool(int(num_proc))
        pool.map_async(_activate_tensors, output_dir.glob('*.vtk'))
        pool.close()
        pool.join()


def test_ukf_tract_querier(num_proc_ukf_tract_querier):
    input_vtk = TEST_DATA / 'dwi.vtk'
    input_query_file = TEST_DATA / 'wmql-2.0.qry'
    input_atlas_file = TEST_DATA / 'fs2dwi' / 'wmparc_in_dwi.nii.gz'
    with local.tempdir() as tmpdir:
        tmpdir = local.path('/tmp/ukf_tract_querier')  # FIXME
        output_dir = tmpdir
        ukf_tract_querier(input_vtk,
                          input_atlas_file,
                          input_query_file,
                          output_dir,
                          num_proc=num_proc_ukf_tract_querier)
        assert len(output_dir // '*.vtk') == 59  # TODO

# class Cli(cli.Application):

#     __doc__ = ukf_tract_querier.__doc__

    # dwi_file = cli.SwitchAttr(
    #     ['--dwi'],
    #     argtype=cli.ExistingFile,
    #     mandatory=True,
    #     help='DWI in NIFTI format')

    # output_dir = cli.SwitchAttr(
    #     ['-o', '--output-dir'],
    #     argtype=cli.NonexistentPath,
    #     mandatory=True,
    #     help='Output directory')

    # num_proc = cli.SwitchAttr(
    #     ['-n', '--num-proc'],
    #     argtype=int,
    #     default=NUM_PROC_ANTS,
    #     help='Number of threads')

#     log_level = cli.SwitchAttr(
#         ['--log-level'],
#         argtype=cli.Set("CRITICAL", "ERROR", "WARNING",
#                         "INFO", "DEBUG", "NOTSET", case_sensitive=False),
#         default='INFO',
#         help='Python log level')

#     def main(self):
#         coloredlogs.install(level=self.level)
#         ukf_tract_querier()
