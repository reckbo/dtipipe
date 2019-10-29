import numpy as np
import nibabel as nib
from plumbum import local


def env_from_bash_file(source_file, init=None):
    init = '' if not init else init
    lines = local['env']('-i', 'bash', '-c', f"{init} source {source_file} && env").strip().split('\n')
    result = {}
    for line in lines:
        var, _, val = line.partition('=')
        result[var] = val
    return result


def fsl_env(fsldir):
    if not fsldir:
        return {}
    fsldir = local.path(fsldir)
    env = env_from_bash_file(fsldir / 'etc' / 'fslconf' / 'fsl.sh')
    env['PATH'] = ':'.join([fsldir / 'bin'] + local.env.path)
    env['FSLDIR'] = fsldir
    return env


def freesurfer_env(freesurfer_home, fsldir):
    fsldir = local.path(fsldir)
    freesurfer_home = local.path(freesurfer_home)
    init = f'FREESURFER_HOME={freesurfer_home} FSL_DIR={fsldir} '
    env = env_from_bash_file(freesurfer_home / 'SetUpFreeSurfer.sh', init=init)
    env['PATH'] = local.path(fsldir / 'bin') + ':' + env['PATH']
    env['FREESURFER_HOME'] = freesurfer_home
    return env


def save_nifti(output_name, data, affine, hdr):
    if data.dtype.name == 'uint8':
        hdr.set_data_dtype('uint8')
    elif data.dtype.name == 'int16':
        hdr.set_data_dtype('int16')
    else:
        hdr.set_data_dtype('float32')
    result_img = nib.Nifti1Image(data, affine, header=hdr)
    result_img.to_filename(output_name)


def compare_niftis(nifti_file1, nifti_file2):
    nifti1 = nib.load(str(nifti_file1))
    nifti2 = nib.load(str(nifti_file2))
    data_is_equal = (np.count_nonzero(nifti1.get_data() - nifti2.get_data()) == 0)
    if not data_is_equal:
        print("Nifti data are not the same:")
        print(nifti_file1)
        print(nifti_file2)
        return False
    headers_are_equal = (nifti1.header == nifti2.header)
    if not headers_are_equal:
        print("Nifti headers are not the same:")
        print(nifti_file1)
        print((nifti1.header.items()))
        print(20*'-')
        print(nifti_file2)
        print((nifti2.header.items()))
        return False
    return True


def read_bvecs(bvec_file, normalize=False):
    with open(bvec_file, 'r') as f:
        bvecs = [[float(num) for num in line.split()] for line in f.read().split('\n') if line]

    # bvec_file can be 3xN or Nx3
    # we want to return as Nx3
    if len(bvecs) == 3:
        bvecs = transpose(bvecs)

    if normalize:
        for i in range(len(bvecs)):
            L_2 = np.linalg.norm(bvecs[i])
            if L_2:
                bvecs[i] /= L_2
            else:
                bvecs[i] = [0, 0, 0]
    return bvecs


def write_bvecs(bvecs, bvec_file):
    with open(bvec_file, 'w') as f:
        f.write(('\n').join((' ').join(str(i) for i in row) for row in bvecs))


def transpose(bvecs):
    return list(map(list, zip(*bvecs)))
