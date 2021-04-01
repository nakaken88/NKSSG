from nkssg.structure.plugins import BasePlugin


class SelectPagesPlugin(BasePlugin):
    def after_initialize_singles(self, singles):
        mode = singles.config.get('mode') or ''
        if mode != 'serve':
            return singles

        start = self.config.get('start') or 0
        end = self.config.get('end') or len(singles.pages)
        step = self.config.get('step') or 1
        singles.pages = singles.pages[start:end:step]
        return singles
