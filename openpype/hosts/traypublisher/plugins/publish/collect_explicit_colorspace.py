import pyblish.api
from openpype.pipeline import registered_host
from openpype.pipeline import publish
from openpype.lib import EnumDef
from openpype.pipeline import colorspace


class CollectColorspace(pyblish.api.InstancePlugin,
                        publish.OpenPypePyblishPluginMixin,
                        publish.ColormanagedPyblishPluginMixin):
    """Collect explicit user defined representation colorspaces"""

    label = "Choose representation colorspace"
    order = pyblish.api.CollectorOrder + 0.49
    hosts = ["traypublisher"]

    colorspace_items = [
        (None, "Don't override")
    ]

    def process(self, instance):
        values = self.get_attr_values_from_data(instance.data)
        colorspace = values.get("colorspace", None)
        self.log.debug("colorspace: {}".format(colorspace))
        if not colorspace:
            return

        context = instance.context
        for repre in instance.data.get("representations", {}):
            self.set_representation_colorspace(
                representation=repre,
                context=context,
                colorspace=colorspace
            )

    @classmethod
    def apply_settings(cls, project_settings):
        host = registered_host()
        host_name = host.name
        project_name = host.get_current_project_name()
        config_data = colorspace.get_imageio_config(
            project_name, host_name,
            project_settings=project_settings
        )

        if config_data:
            filepath = config_data["path"]
            config_items = colorspace.get_ocio_config_colorspaces(filepath)
            cls.colorspace_items.extend((
                (name, name)
                for name, family in config_items.items()
            ))
        else:
            cls.colorspace_items.extend([
                ("sRGB", "sRGB"),
                ("rec709", "rec709"),
                ("ACES", "ACES"),
                ("ACEScg", "ACEScg")
            ])

    @classmethod
    def get_attribute_defs(cls):
        return [
            EnumDef(
                "colorspace",
                cls.colorspace_items,
                default="Don't override",
                label="Override Colorspace"
            )
        ]
