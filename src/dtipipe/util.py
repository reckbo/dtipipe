import nibabel as nib
from plumbum import local


def source_shell_file(source_file):
    lines = local['env']('-i', 'bash', '-c', f"source {source_file} && env").strip().split('\n')
    result = {}
    for line in lines:
        var, _, val = line.partition('=')
        result[var] = val
    return result


def fsl_env(fsldir):
    if not fsldir:
        return {}
    new_path = [fsldir + '/bin'] + local.env.path
    fsl_env = source_shell_file(fsldir + '/etc/fslconf/fsl.sh')
    return dict(**fsl_env, PATH=':'.join(new_path))


def save_nifti(output_name, data, affine, hdr):
    if data.dtype.name == 'uint8':
        hdr.set_data_dtype('uint8')
    elif data.dtype.name == 'int16':
        hdr.set_data_dtype('int16')
    else:
        hdr.set_data_dtype('float32')
    result_img = nib.Nifti1Image(data, affine, header=hdr)
    result_img.to_filename(output_name)
