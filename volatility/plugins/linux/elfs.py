"""A module containing a collection of plugins that produce data
typically found in Linux's /proc file system.
"""
import typing

from volatility.framework import renderers, interfaces
from volatility.framework.configuration import requirements
from volatility.framework.interfaces import plugins
from volatility.framework.objects import utility
from volatility.framework.renderers import format_hints
from volatility.plugins.linux import pslist


class Elfs(plugins.PluginInterface):
    """Lists all memory mapped ELF files for all processes"""

    @classmethod
    def get_requirements(cls) -> typing.List[interfaces.configuration.RequirementInterface]:
        return [requirements.TranslationLayerRequirement(name = 'primary',
                                                         description = 'Kernel Address Space',
                                                         architectures = ["Intel32", "Intel64"]),
                requirements.SymbolRequirement(name = "vmlinux",
                                               description = "Linux Kernel")]

    def _generator(self, tasks):
        for task in tasks:
            proc_layer_name = task.add_process_layer()
            if proc_layer_name == None:
                continue

            proc_layer = self.context.memory[proc_layer_name]

            name = utility.array_to_string(task.comm)

            for vma in task.mm.mmap_iter:
                hdr = proc_layer.read(vma.vm_start, 4, pad = True)
                if not (hdr[0] == 0x7f and hdr[1] == 0x45 and hdr[2] == 0x4c and hdr[3] == 0x46):
                    continue

                path = vma.get_name(task)

                yield (
                    0,
                    (task.pid,
                     name,
                     format_hints.Hex(vma.vm_start),
                     format_hints.Hex(vma.vm_end),
                     path
                     ))

    def run(self):
        filter = pslist.PsList.create_filter([self.config.get('pid', None)])

        plugin = pslist.PsList.list_tasks

        return renderers.TreeGrid(
            [("PID", int),
             ("Process", str),
             ("Start", format_hints.Hex),
             ("End", format_hints.Hex),
             ("File Path", str)],
            self._generator(plugin(self.context,
                                   self.config['primary'],
                                   self.config['vmlinux'],
                                   filter = filter)))