from nkssg.structure.plugins import BasePlugin
from nkssg.structure.singles import Singles


class SelectPagesPlugin(BasePlugin):
    def after_initialize_singles(self, singles: Singles):
        mode = singles.config.get('mode', '')
        if mode != 'serve':
            return singles

        start = self.config.get('start', 0)
        end = self.config.get('end', len(singles.pages))
        step = self.config.get('step', 1)
        singles.pages = singles.pages[start:end:step]
        return singles
