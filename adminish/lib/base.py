from restish import page, resource
from adminish.lib import flash



class BaseResource(resource.Resource):
    pass


class BasePage(page.Page):
    @page.element('flash_message')
    def flash_message(self, request):
        """
        Return a flash message box element.
        """
        return flash.FlashMessagesElement() 
    



class BaseElement(page.Element):
    pass

