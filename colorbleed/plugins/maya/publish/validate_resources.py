import pyblish.api
import colorbleed.api

import os


class ValidateResources(pyblish.api.InstancePlugin):
    """Validates mapped resources.

    These are external files to the current application, for example
    these could be textures, image planes, cache files or other linked
    media.

    This validates:
        - The resources are existing files.
        - The resources have correctly collected the data.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = "Resources"

    def process(self, instance):

        for resource in instance.data.get('resources', []):

            # Required data
            assert "source" in resource
            assert "destination" in resource
            assert "files" in resource
            assert all(os.path.exists(f) for f in resource['files'])
