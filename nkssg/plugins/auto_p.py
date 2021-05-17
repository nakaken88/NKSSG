from nkssg.structure.plugins import BasePlugin


class AutoPPlugin(BasePlugin):
    def __init__(self):
        self.block_tags = []


    def on_get_content(self, doc, config, single, **kwargs):
        self.block_tags = config['block_tags']
        if single.ext in ["html", "htm", "txt"]:
            content = self.autoP(doc)
        else:
            content = doc
        return content

    def autoP(self, doc):
        block_tags = self.block_tags

        block_tag_count = {}
        for block_tag in block_tags:
            block_tag_count[block_tag] = 0


        blocks = doc.splitlines()
        lines = []
        i = 0

        for block in blocks:

            for block_tag in block_tags:
                if '<' + block_tag + ' ' in block or '<' + block_tag + '>' in block:
                    block_tag_count[block_tag] = block_tag_count[block_tag] + 1

            is_block = False
            for v in block_tag_count.values():
                if v > 0:
                    is_block = True

            new_block = block
            if (not is_block) and new_block != "":
                if i == 0 or blocks[i - 1] == '':
                    new_block = '<p>' + new_block
                if i == len(blocks) - 1 or blocks[i + 1] == '':
                    new_block = new_block + '</p>'
                else:
                    new_block = new_block + '<br />'

            if "blockquote" in new_block:
                new_block = new_block.replace("<p><blockquote>", "<blockquote><p>")
                new_block = new_block.replace("</blockquote></p>", "</p></blockquote>")

            lines.append(new_block)


            for block_tag in block_tags:
                if '</' + block_tag in block:
                    block_tag_count[block_tag] = block_tag_count[block_tag] - 1

            if '<hr>' in block:
                block_tag_count['hr'] = block_tag_count['hr'] - 1
            if '<hr />' in block:
                block_tag_count['hr'] = block_tag_count['hr'] - 1

            i = i + 1

        return '\n'.join(lines)
