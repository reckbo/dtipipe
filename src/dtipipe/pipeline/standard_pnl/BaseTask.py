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

    def commandline_args(self):
        kwargs = self.param_kwargs
        task_args = ' '.join([f'--{k.replace("_", "-")} "{v}"' for (k, v) in kwargs.items()])
        import inspect
        task_module = inspect.getmodule(self).__name__
        return f'--module {task_module} {self.task_family} {task_args} --local-scheduler'


class BaseTask(luigi.Task, BaseMethods):
    pass


class BaseWrapperTask(luigi.WrapperTask, BaseMethods):
    pass
