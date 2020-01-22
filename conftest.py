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
        "--ukf-bin", action="store", default=None, help="Path to root UKFTractography binary"
    )
    parser.addoption(
        "--num-proc-ants", action="store", default=10, help="Number of threads for ANTs"
    )
    parser.addoption(
        "--num-proc-eddy", action="store", default=10, help="Number of threads for eddy_pnl"
    )
    parser.addoption(
        "--num-proc-ukf-tract-querier", action="store", default=10,
        help="Number of threads for ukf_tract_querier"
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
def ukf_tractography_bin(request):
    return request.config.getoption("--ukf-bin")


@pytest.fixture
def num_proc_eddy(request):
    return request.config.getoption("--num-proc-eddy")


@pytest.fixture
def num_proc_ants(request):
    return request.config.getoption("--num-proc-ants")


@pytest.fixture
def num_proc_ukf_tract_querier(request):
    return request.config.getoption("--num-proc-ukf-tract-querier")
