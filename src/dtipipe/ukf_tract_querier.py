import filecmp
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
    activate_tensors.activate_tensors(vtk_file, new_vtk_file)
    vtk_file.delete()


def ukf_tract_querier(ukf_vtk, atlas_file, query_file, output_dir, num_proc=DEFAULT_NUM_PROC):
    """
    Wrapper around tract_querier that first removes short tracts from the input tractography file
    and following tract_querier converts nan's and inf's to 0's and large finite numbers.
    """

    ukf_vtk = local.path(ukf_vtk)
    atlas_file = local.path(atlas_file)
    query_file = local.path(query_file)
    output_dir = local.path(output_dir)

    if output_dir.exists():
        raise Exception(f'{output_dir} already exists')

    with local.tempdir() as tmpdir:

        pruned_ukf_vtk = tmpdir / 'pruned_ukf.vtk'
        tmp_output_dir = tmpdir / 'output'
        tmp_output_dir.mkdir()

        log.info(f'Remove short tracts from the tractography file (Make {pruned_ukf_vtk})')
        r = local['tract_math'].run([ukf_vtk, 'tract_remove_short_tracts', '2', pruned_ukf_vtk])
        log.debug(f'tract_math output: {r}')
        if not pruned_ukf_vtk.exists():
            raise Exception(f'tract_math failed to make {pruned_ukf_vtk}\n'
                            f'tract_math output: {r}')

        log.info(f'Run tract_querier (Make {tmp_output_dir}/*.vtk)')
        local['tract_querier'].run(['-t', pruned_ukf_vtk,
                                    '-a', atlas_file,
                                    '-q', query_file,
                                    '-o', tmp_output_dir / '_'])

        log.info(f"Update the tensor data format in each output vtk and replace nan's with 0 "
                 "and inf's with large finite numbers")
        pool = Pool(int(num_proc))
        pool.map_async(_activate_tensors, tmp_output_dir.glob('*.vtk'))
        pool.close()
        pool.join()

        log.info(f'Copy {tmp_output_dir} to {output_dir}')
        output_dir.parent.mkdir()
        tmp_output_dir.copy(output_dir)


def test_ukf_tract_querier(num_proc_ukf_tract_querier):
    input_vtk = TEST_DATA / 'dwi.vtk'
    input_query_file = TEST_DATA / 'wmql-2.0.qry'
    input_atlas_file = TEST_DATA / 'fs2dwi' / 'wmparc_in_dwi.nii.gz'
    expected_output_vtks = sorted(TEST_DATA / 'ukf_tract_querier' // '*.vtk')
    with local.tempdir() as tmpdir:
        tmpdir = local.path('/tmp/ukf_tract_querier')  # FIXME
        output_dir = tmpdir
        ukf_tract_querier(input_vtk,
                          input_atlas_file,
                          input_query_file,
                          output_dir,
                          num_proc=num_proc_ukf_tract_querier)
        output_vtks = sorted(output_dir // '*.vtk')
        assert len(output_vtks) == len(expected_output_vtks)
        for (output, expected) in zip(output_vtks, expected_output_vtks):
            assert filecmp.cmp(output, expected)


class Cli(cli.Application):

    __doc__ = ukf_tract_querier.__doc__

    input_vtk = cli.SwitchAttr(
        ['-t', '--tractography-file'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='Input tractography VTK file')

    input_atlas_file = cli.SwitchAttr(
        ['-a', '--atlas'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='Input atlas file (e.g. dwi_in_wmparc.nii.gz)')

    input_query_file = cli.SwitchAttr(
        ['-q', '--query'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='Input query file (.qry)')

    output_dir = cli.SwitchAttr(
        ['-o', '--output-dir'],
        argtype=cli.NonexistentPath,
        mandatory=True,
        help='Output directory where VTK tracts will be saved to')

    num_proc = cli.SwitchAttr(
        ['-n', '--num-proc'],
        argtype=int,
        default=DEFAULT_NUM_PROC,
        help='Number of threads used in postprocessing the generated VTK tracts')

    log_level = cli.SwitchAttr(
        ['--log-level'],
        argtype=cli.Set("CRITICAL", "ERROR", "WARNING",
                        "INFO", "DEBUG", "NOTSET",
                        case_sensitive=False),
        default='INFO',
        help='Python log level')

    def main(self):
        coloredlogs.install(level=self.log_level)
        ukf_tract_querier(self.input_vtk,
                          self.input_atlas_file,
                          self.input_query_file,
                          self.output_dir,
                          num_proc=self.num_proc)
