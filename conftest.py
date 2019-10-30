import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--fsldir", action="store", default=None, help="Path to root FSL installation"
    )
    parser.addoption(
        "--fshome", action="store", default=None, help="Path to root FreeSurfer installation"
    )
    parser.addoption(
        "--antspath", action="store", default=None, help="Path to root ANTs bin/ directory"
    )
    parser.addoption(
        "--num-proc-ants", action="store", default=10, help="Number of threads for ANTs"
    )


@pytest.fixture
def fsldir(request):
    return request.config.getoption("--fsldir")


@pytest.fixture
def freesurfer_home(request):
    return request.config.getoption("--fshome")


@pytest.fixture
def antspath(request):
    return request.config.getoption("--antspath")


@pytest.fixture
def num_proc_ants(request):
    return request.config.getoption("--num-proc-ants")
