import re
from urllib.parse import quote

from nkssg.structure.config import Config
from nkssg.structure.plugins import BasePlugin
from nkssg.structure.site import Site


class BacklinkPlugin(BasePlugin):

    href_pattern = re.compile(
        r'<a\s+'                # Opening tag and space
        r'[^>]*?'               # Any attributes
        r'href\s*=\s*'          # href attribute
        r'["\'](.*?)["\']',     # Attribute value
        re.I | re.S
    )

    @staticmethod
    def extract_urls_from_html(html_content):
        return BacklinkPlugin.href_pattern.findall(html_content)

    @staticmethod
    def clean_url(href: str, config: Config):
        href = href.lower()

        if 'http' in href:
            if config.site.site_url in href:
                href = href.replace(config.site.site_url, '')
            elif config.site.site_url_original in href:
                href = href.replace(config.site.site_url_original, '')
            else:
                return None

        href = href.split('#')[0]
        href = href.split('?')[0]
        return href

    def after_update_urls(self, site: Site, **kwargs):
        for page in site.singles:
            page.to_links = set()
            page.back_links = set()
            page.to_links_text = set()

            for href in BacklinkPlugin.extract_urls_from_html(page.content):
                cleaned_href = BacklinkPlugin.clean_url(href, site.config)
                if cleaned_href:
                    page.to_links_text.add(cleaned_href)

        urls = {str(page.rel_url).lower(): page for page in site.singles}
        for page in site.singles:
            for link in page.to_links_text:
                to_page = urls.get(quote(link))
                if to_page:
                    page.to_links.add(to_page)
                    to_page.back_links.add(page)
