from adminish import markdown, mdx_enhanced_image

def md(text):
    return markdown.markdown(text, [mdx_enhanced_image])
