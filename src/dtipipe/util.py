import pandas as pd
import numpy as np
import nibabel as nib
from plumbum import local


def env_from_bash_file(source_file, init=None):
    init = '' if not init else init
    lines = local['env']('-i', 'bash', '-c', f"{init} source {source_file} && env").strip() \
                                                                                   .split('\n')
    result = {}
    for line in lines:
        var, _, val = line.partition('=')
        result[var] = val
    return result


def get_fsl_env(fsldir):
    if not fsldir:
        return {}
    fsldir = local.path(fsldir)
    env = env_from_bash_file(fsldir / 'etc' / 'fslconf' / 'fsl.sh')
    env['PATH'] = ':'.join([fsldir / 'bin'] + local.env.path)
    env['FSLDIR'] = fsldir
    return env


def fsl_env(fsldir):
    env = get_fsl_env(fsldir)
    return local.env(**env)


def get_freesurfer_env(freesurfer_home, fsldir):
    fsldir = local.path(fsldir)
    freesurfer_home = local.path(freesurfer_home)
    init = f'FREESURFER_HOME={freesurfer_home} FSL_DIR={fsldir} '
    env = env_from_bash_file(freesurfer_home / 'SetUpFreeSurfer.sh', init=init)
    env['PATH'] = local.path(fsldir / 'bin') + ':' + env['PATH']
    env['FREESURFER_HOME'] = freesurfer_home
    return env


def freesurfer_env(freesurfer_home, fsldir):
    env = get_freesurfer_env(freesurfer_home, fsldir)
    return local.env(**env)


def get_ants_env(antspath):
    if not antspath:
        return {}
    antspath = local.path(antspath)
    path = ':'.join([antspath] + local.env.path)
    return dict(PATH=path, ANTSPATH=antspath)


def ants_env(ants_dir):
    env = get_ants_env(ants_dir)
    return local.env(**env)


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


def read_bvals(bval_file):
    return [float(i) for i in bval_file.read().strip().split()]


def write_bvecs(bvecs, bvec_file):
    with open(bvec_file, 'w') as f:
        f.write(('\n').join((' ').join(str(i) for i in row) for row in bvecs))


def bvec_scaling(bval, bvec, b_max):
    if bval:
        factor = np.sqrt(bval / b_max)
        if np.linalg.norm(bvec) != factor:
            bvec = np.array(bvec) * factor
    bvec = [str(x) for x in bvec]
    return ('   ').join(bvec)


def transpose(bvecs):
    return list(map(list, zip(*bvecs)))


def read_freesurfer_stats_header(stats_file):
    header = None
    for line in open(stats_file, 'r'):
        if line.startswith('# ColHeaders'):
            header = line.split()[2:]
            break
    return header


def read_freesurfer_stats(stats_file):
    header = read_freesurfer_stats_header(stats_file)
    if not header:
        raise Exception(f'Failed to find header in stats file: {stats_file}')
    return pd.read_csv(stats_file, names=header, comment='#', delim_whitespace=True)
