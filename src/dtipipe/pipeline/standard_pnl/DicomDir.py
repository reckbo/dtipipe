from plumbum import local
from luigi import Parameter, ExternalTask


class DicomDir(ExternalTask):

    dicom_dir = Parameter()

    def output(self):
        return local.path(self.dicom_dir.strip())
