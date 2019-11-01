import logging
import filecmp

import vtk
import numpy
from plumbum import local
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk

from . import TEST_DATA


log = logging.getLogger(__name__)


def activate_tensors(input_vtk, output_vtk):
    """
    Replaces the tensor data's nan's with 0 and inf's with large finite
    numbers, and calls VTK's 'SetTensors' on the tensor data.
    """

    log.info(f'Read in VTK file: {input_vtk}')
    poly_data_reader = vtk.vtkPolyDataReader()
    poly_data_reader.SetFileName(input_vtk)
    poly_data_reader.Update()
    output = poly_data_reader.GetOutput()
    point_data = output.GetPointData()

    log.info('Get first tensor')
    tensors = point_data.GetArray('tensor1')
    if not tensors:
        tensors = point_data.GetTensors()

    log.info("Replace nan's with 0 and inf's with large finite numbers and set tensor attribute")
    if tensors is not None:
        np_tensors = vtk_to_numpy(tensors)
        np_tensors = numpy.nan_to_num(np_tensors)
        tensors = numpy_to_vtk(np_tensors)
        point_data.SetTensors(tensors)

    log.info(f'Write output: {output_vtk}')
    poly_data_writer = vtk.vtkPolyDataWriter()
    poly_data_writer.SetFileTypeToBinary()
    poly_data_writer.SetFileName(output_vtk)
    poly_data_writer.SetTensorsName('tensor1')
    #  poly_data_writer.SetInput(output_vtk)
    poly_data_writer.SetInputData(output)
    poly_data_writer.Write()
    poly_data_writer.Update()


def test_activate_tensors():
    expected_output_vtk = TEST_DATA / 'cc.vtk'
    input_vtk = TEST_DATA / '__cc.vtk'
    with local.tempdir() as tmpdir:
        output_vtk = tmpdir / 'cc.vtk'
        activate_tensors(input_vtk, output_vtk)
        assert filecmp.cmp(output_vtk, expected_output_vtk)
