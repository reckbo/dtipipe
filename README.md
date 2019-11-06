An implementation of PNL's DTI processing scripts and pipelines.  Pipelines
are implemented using [Luigi](https://github.com/spotify/luigi).


# Install

## Using Poetry

[poetry](https://poetry.eustace.io/)

```shell
poetry add --git https://github.com/reckbo/dtipipe
```

## Using Pip

If using virtualenv:

```shell
virtualenv .venv --python=python3
source .venv/bin/activate{.*sh}
```

Numpy needs to be installed first otherwise `tract_querier` fails to install:

```shell
pip install numpy
pip install git+https://github.com/reckbo/dtitpipe
```

# Scripts

| Script                      | Description                                                                                                |
|-----------------------------|------------------------------------------------------------------------------------------------------------|
| bse                         | Extracts the baseline (B0) from a nifti DWI                                                                |
| eddy_pnl                    | Performs eddy current correction by registering each volume to the first B0                                |
| bet_mask                    | Create a mask using FSL's bet                                                                              |
| apply_antsRegistrationSyNMI | Runs antsRegistrationSyNMI.sh script to compute a transformation and then applies it to the target volume. |
| fs2dwi                      | Registers Freesurfer labelmap to DWI space.                                                                |
| nifti2nhdr                  | Convert a nifti to nrrd by creating an nhdr header                                                         |
| ukf                         | Run UKFTractography given a DWI and DWI mask in NIFTI format                                               |
| ukf_tract_querier           | Wrapper around tract_querier that removes short tracts and converts nan's/inf's to 0's and large numbers   |


To run a script, simply activate your python environment and call the script, e.g

```shell
source .venv/bin/activate{.*sh*}
ukf --help
```

```shell
poetry run ukf --help
```

or

```shell
poetry shell
ukf --help
```


# Pipelines

Pipelines are implemented using [Luigi](https://github.com/spotify/luigi), and are saved under `src/dtipipe/pipelines`.

Here's an example on how to initialize and run a pipeline for a particular session.

First, configure your default parameters and software locations and use those as
input to the `UKFTracts` task, which is the `standard_pnl` pipeline's final output.


```python
from plumbum import local
from dtipipe.pipeline import standard_pnl

OUTPUT_DIR = local.path(__file__).parent.parent.parent / 'output'

# Parameters
DWI_BET_MASK_THRESHOLD = 0.1

# Software
SOFTWARE = local.path('/cluster/software')
UKFTRACTOGRAPHY_BIN = SOFTWARE / 'UKFTractography-017c06f'
ANTSPATH = SOFTWARE / 'ANTs-build' / 'bin'
FSL_DIR_5_0_7 = local.path('/usr/packages/fsl/5.0.7')
FSL_DIR_6_0_1 = local.path('/usr/packages/fsl/6.0.1')
FREESURFER_HOME_6 = local.path('/usr/local/freesurfer/stable6')

# Control
NUM_PROC_EDDY = 25
NUM_PROC_ANTS = 25
NUM_PROC_ANTS_UKF_TRACT_QUERIER = 25


def make_task(subject_id, session_id, dwi_dicom_dir, freesurfer_recon_dir):
    return UkfTracts(dicom_dir=dwi_dicom_dir,
                     freesurfer_recon_dir=freesurfer_recon_dir,
                     output_session_dir=OUTPUT_DIR / subject_id / session_id
                     output_basename='dwi',
                     dwi_bet_mask_threshold=dwi_bet_mask_threshold,
                     ukf_params={},
                     fsldir=fsldir,
                     antspath=antspath,
                     freesurfer_home=freesurfer_home,
                     ukftractography_bin=UKFTRACTOGRAPHY_BIN,
                     num_proc_eddy=num_proc_eddy,
                     num_proc_ants=num_proc_ants,
                     num_proc_ukf_tract_querier=num_proc_ukf_tract_querier)
```

Now you can create and run the Luigi task:

```python
import luigi
ukf_tracts_task = make_task('subject_001', 'session_001', '/data/subject_001/session_001/dwi_dicoms/',  
                            '/data/subject_001/session_001/freesurfer_recon')
luigi.build([ukf_tracs_task], workers=1)
```
