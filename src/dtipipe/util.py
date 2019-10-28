from plumbum import local


def source_shell_file(source_file):
    lines = local['env']('-i', 'bash', '-c', f"source {source_file} && env").strip().split('\n')
    result = {}
    for line in lines:
        var, _, val = line.partition('=')
        result[var] = val
    return result


def get_fsl_env(fsldir):
    new_path = [fsldir + '/bin'] + local.env.path
    fsl_env = source_shell_file(fsldir + '/etc/fslconf/fsl.sh')
    return dict(**fsl_env, PATH=':'.join(new_path))
