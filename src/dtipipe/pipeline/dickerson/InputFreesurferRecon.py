import os

from plumbum import LocalPath
from luigi import Parameter, ExternalTask

from dtipipe import util


RECON_SUBPATHS = ['mri/orig.mgz',
                  'mri/T1.mgz',
                  'mri/brainmask.mgz',
                  'mri/aparc+aseg.mgz',
                  'mri/wm.mgz',
                  'surf/lh.white',
                  'surf/rh.white',
                  'surf/lh.pial',
                  'surf/rh.pial',
                  'label/lh.aparc.annot',
                  'label/rh.aparc.annot']


class LocalDir(LocalPath):

    def __new__(cls, *parts, subpaths=None):
        self = super().__new__(cls, *parts)
        if isinstance(subpaths, str):
            subpaths = [subpaths]
        self.subpaths = subpaths
        return self

    def exists(self):
        if self.subpaths:
            return all((self / subpath).exists() for subpath in self.subpaths)
        return os.path.exists(str(self))

    def missing(self):
        if self.subpaths:
            return [(self / subpath) for subpath in self.subpaths if not (self / subpath).exists()]
        if not self.exists():
            return [self]
        return []


class InputFreesurferRecon(ExternalTask):

    freesurfer_recon_dir = Parameter()

    def output(self):
        return LocalDir(self.freesurfer_recon_dir, subpaths=RECON_SUBPATHS)

    def read_stats(self, stats_file):
        return util.read_freesurfer_stats(self.output() / 'stats' / stats_file)
