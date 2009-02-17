"""
"Flash" messaging support.

A "flash" message is a message displayed on a web page that is removed next
request.
"""

from wsgiapptools import flash
from restish import page

from adminish.lib import templating


# Expose useful bits of the wsgiapptools.flash module.
add_message = flash.add_message
get_messages = flash.get_messages
get_flash = flash.get_flash
flash_middleware_factory = flash.flash_middleware_factory


class FlashMessagesElement(page.Element):
    """
    A messages element renders a template that will display a list of messages
    if the request includes a 'flash' cookie.

    The messages can include an optional type by prefixing the message with the
    type and a ':', e.g. "success:It worked", "error:You can't do that just
    now", etc.

    Recommended types are:

        * error - something went horribly wrong
        * info - something interesting happened
        * success - whatever the user did was successful
        * warning - something gone a bit weird
    """

    def __call__(self, request):
        messages = get_messages(request.environ)
        if not messages:
            return ''
        return templating.render(request, 'flash_messages.html',
                                 {'messages': messages})

