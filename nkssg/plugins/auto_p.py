import markdown

from nkssg.structure.plugins import BasePlugin


class AutoPPlugin(BasePlugin):
    def on_get_content(self, doc, config, single, **kwargs):
        if single.ext in ["html", "htm", "txt"]:
            content = markdown.markdown(doc, extensions=['nl2br'])
        else:
            content = doc
        return content
