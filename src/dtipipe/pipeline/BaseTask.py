import luigi
import luigi.tools.deps
import toolz


class BaseMethods(object):

    def build(self, local_scheduler=True, **kwargs):
        luigi.build([self], local_scheduler=local_scheduler, **kwargs)

    def ancestor_tasks(self):
        return set(toolz.concat([luigi.tools.deps.find_deps(t, None) for t in self.deps()]))

    def delete(self):
        self.output().delete()

    def rebuild(self, **kwargs):
        self.delete()
        self.build(**kwargs)

    def clone_self(self, **kwargs):
        return self.clone(self.__cls__, **kwargs)


class BaseTask(luigi.Task, BaseMethods):
    pass


class BaseWrapperTask(luigi.WrapperTask, BaseMethods):
    pass
