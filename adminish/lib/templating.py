"""
Templating support library and renderer configuration.
"""

from restish import templating


def make_renderer(app_conf):
    """
    Create and return a restish.templating "renderer".
    """

    # Uncomment for an example of Mako templating support.
    import pkg_resources
    import os.path
    from restish.contrib.makorenderer import MakoRenderer
    return MakoRenderer(
            directories=[
                pkg_resources.resource_filename('adminish', 'templates'),
                pkg_resources.resource_filename('formish', 'templates/mako'),
                ],
            module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
            input_encoding='utf-8', output_encoding='utf-8',
            default_filters=['unicode', 'h']
            )

    return None


# Subclass the standard Rendering type. Overriding Rendering methods make it
# trivial to push extra, application-wide data to the templates without any
# assistance from the resource.
class Rendering(templating.Rendering):
    pass


# Expose the decorators at module-scope, just like restish.templating.
_rendering = Rendering()
render = _rendering.render
page = _rendering.page
element = _rendering.element

