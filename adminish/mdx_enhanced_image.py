#!/usr/bin/env python

'''
Insert CMS Image 
================

Adds extra attributes to the image tag syntax in markdown

Basic usage:

    >>> import markdown
    >>> text = 'Some text with a ![alttxt](http://x.com/ "title" maxwidth=8 maxheight=9 caption="way too small")(myurl)'
    >>> md = markdown.markdown(text, ['cmsimage'])

'''

import markdown

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[(' \
  + (NOBRACKET + r'(\['+NOBRACKET)*6 \
  + (NOBRACKET+ r'\])*'+NOBRACKET)*6 \
  + NOBRACKET + r')\]' )
ENHANCED_IMAGE_LINK_RE = r'\!' + BRK + r'\s*\(([^\)" ]*)\s*(?:"([^\)"]*)")?([^\)]*)\)\(?([^\)]*)\)?'

def ParseOptions(optiontext):
    if optiontext.strip() == '':
        return {}
    state='outside'
    out=[]
    for char in optiontext:
        if char=='"' and state=='outside':
            state='inside'
            continue
        if char=='"' and state=='inside':
            state='outside'
            continue
        if char==' ' and state=='inside':
            char="\t"
        out.append(char)
    out = ''.join(out)
    optionstrings = out.split(' ')
    options={}
    for option in optionstrings:
        k,v = option.split('=')
        options[k]=v.replace('\t',' ')
    return options


class EnhancedImage(markdown.Pattern):

    def __init__(self,pattern,context):
        self.context=context[0]
        markdown.Pattern.__init__(self,pattern)
    
    def handleMatch(self, m, doc):
        alt = m.group(2).strip()

        optiontext = m.group(11).strip()
        options=ParseOptions(optiontext)
        src = m.group(9).strip()
        if src.startswith('cmsimage://'):
            imageId = src[11:]
            if self.context == 'public':
                src = '/system/assets/%s'%imageId
            else: 
                src = '/content/system/assets/%s'%imageId
                
        if options.has_key('maxheight') and options.has_key('maxwidth'):
            src = '%s?size=%sx%s'%(src,options['maxwidth'],options['maxheight'])
        link = m.group(12)
        
        el = doc.createElement('img')
        el.setAttribute('src', src)
        el.setAttribute('alt', alt)
        title = m.group(10)
        if title is not None:
            el.setAttribute('title', title.strip())
        if options.has_key('cssclass'):
            el.setAttribute('class', options['cssclass'] )
        if link != '':
            a = doc.createElement('a')
            a.setAttribute('href',link)
            a.appendChild(el)
            out = a
        else:
            out = el
        if options.has_key('caption'):
            dl = doc.createElement('dl')
            dt = doc.createElement('dt')
            dd = doc.createElement('dd')
            dt.appendChild(out)
            dd.appendChild(doc.createTextNode(options['caption']))
            dl.appendChild(dt)
            dl.appendChild(dd)
            out = dl
        return out


class EnhancedImageExtension (markdown.Extension):
    
    def __init__ (self, configs) :

        self.config = {'context' :
                       ["public",
                        "Which mode to convert in. In admin mode, item selectors just show a placeholder"]}
        for key, value in configs :
            self.setConfig(key, value)
    

    def extendMarkdown(self, md, md_globals):
        self.md = md
        # inline patterns
        index = md.inlinePatterns.index(md_globals['IMAGE_LINK_PATTERN'])
        inlinepattern = EnhancedImage(ENHANCED_IMAGE_LINK_RE,context=self.config['context'])
        inlinepattern.md = md
        md.inlinePatterns.insert(index,inlinepattern)
    
def makeExtension(configs=None) :
    return EnhancedImageExtension(configs=configs) 
