from io import StringIO
import os
import re
import dotenv
from collections import defaultdict
import mwparserfromhell
from mwparserfromhell.nodes.template import Template
from mwparserfromhell.nodes.tag import Tag
from mwparserfromhell.wikicode import Wikicode
import logging


import pandas as pd

from stardewkg.utils.utils import format_page_name


def extract_nested_templates(value):
    nested_templates = []
    if isinstance(value, mwparserfromhell.wikicode.Wikicode):
        for node in value.ifilter_templates(recursive=True):
            nested_templates.append(node)
    return nested_templates


def get_headings(wikicode: Wikicode):
    return wikicode.filter_headings()


def get_heading_content(wikitext: str, heading: str) -> str:
    parsed = mwparserfromhell.parse(wikitext)
    sections = parsed.get_sections(include_lead=True)

    for section in sections:
        if not section.filter_headings():
            continue

        parsed_heading = section.filter_headings()[0].title.strip_code().strip()
        if str(parsed_heading) == heading:
            return "\n".join(section.splitlines()[1:])


def get_tables(text) -> Tag:
    parsed = mwparserfromhell.parse(text)
    return parsed.filter_tags(matches=lambda node: node.tag == "table")


def wiki_link_to_html(node):
    text = str(node.title)
    return f'<a href="#">{text}</a>'


def wiki_table_to_html(node: Tag):
    result = ["<table>"]
    for row in node.contents.nodes:
        if isinstance(row, mwparserfromhell.nodes.Tag) and row.tag == "tr":
            result.append("<tr>")
            for cell in row.contents.nodes:
                if isinstance(cell, mwparserfromhell.nodes.Tag) and cell.tag in [
                    "td",
                    "th",
                ]:
                    result.append(f"<{cell.tag}>")
                    for content in cell.contents.nodes:
                        if isinstance(content, mwparserfromhell.nodes.Text):
                            result.append(str(content))
                        elif isinstance(content, mwparserfromhell.nodes.Wikilink):
                            result.append(wiki_link_to_html(content))
                    result.append(f"</{cell.tag}>")
            result.append("</tr>")
    result.append("</table>")
    return "".join(result)


def read_wikitable(table) -> pd.DataFrame:
    html_text = wiki_table_to_html(table)
    return pd.read_html(StringIO(html_text))[0]


def extract_standalone_links(text):
    pattern = r"^\s*(\[\[.*?\]\])\s*$"
    links = re.findall(pattern, text, flags=re.MULTILINE)
    links = [mwparserfromhell.parse(link).filter_wikilinks()[0] for link in links]
    return links


class SourceParser:
    def __init__(self, title: str, source: str = None):
        self.title = title
        self.source = source

        self.wikicode: Wikicode = mwparserfromhell.parse(
            self.source, skip_style_tags=True
        )
        self.templates: list[Template] = self.wikicode.filter_templates()

        # Infobox parsing
        self.name = format_page_name(self.title)
        self.infobox = self.extract_infobox()
        self.infobox_type = self.extract_infobox_type()
        self.infobox_params = self.extract_infobox_params()

        # Body parsing
        self.headings = self.get_headings()
        self.categories = self.get_categories()

    def __str__(self):
        return f"SourceParser(infobox_type={self.infobox_type},infobox_param={self.infobox_params})"
        pass

    def __repr__(self):
        return f"SourceParser(infobox_type={self.infobox_type},infobox_param={self.infobox_params})"
        pass

    def extract_infobox(self) -> Template | None:
        # Check if there is an infobox
        for template in self.templates:
            if "Infobox" in template.name:
                return template

        return None

    def extract_infobox_type(self) -> str:
        if not self.infobox:
            return None

        line = self.infobox.splitlines()[0]

        # Check if infobox type exists
        if line.endswith("Infobox"):
            return "unknown"
        return line.split(" ")[-1].strip().replace("}", "")

    def extract_infobox_params(self) -> dict:
        if not self.infobox:
            return None

        infobox_params = defaultdict(dict)
        for param in self.infobox.params:
            param_name = str(param.name).strip()
            param_value = param.value

            # Handle nested values
            nested_templates = extract_nested_templates(param_value)
            nested_templates_str = ""  # needed to handle unwanted data filtering
            if nested_templates:
                # print(f"Parameter: {param_name}")
                for nested_template in nested_templates:
                    nested_templates_str += str(nested_template)
                    # print(f"  - Found nested template: {nested_template}")
                    # print(nested_template.name, nested_template.params)
                    try:
                        infobox_params[str(param_name)][
                            str(nested_template.params[0])
                        ] = [nested_template.name, nested_template.params]
                    except IndexError:
                        logging.debug("Failed to parse nested template in infobox")
                        logging.debug(self.title)
                        logging.debug(param_name, nested_template)

                # Get eventual data that got filtered when filtering the template
                # For example the villager birthday value
                filtered = str(param_value).strip().replace(nested_templates_str, "")
                if len(filtered) > 0:
                    infobox_params[str(param_name)]["data"] = filtered.strip()
            else:
                infobox_params[str(param_name)] = param_value.strip()

        return dict(infobox_params)

    def get_headings(self, level: int = None) -> list[str]:
        headings = self.wikicode.filter_headings()
        if not level:
            return [str(heading.title) for heading in headings]
        else:
            return [
                str(heading.title) for heading in headings if heading.level == level
            ]

    def get_heading_content(self, heading: str) -> str:
        sections = self.wikicode.get_sections(include_lead=True)

        for section in sections:
            if not section.filter_headings():
                continue

            parsed_heading = section.filter_headings()[0].title.strip_code().strip()
            if str(parsed_heading) == heading:
                return "\n".join(section.splitlines()[1:])

    def get_categories(self) -> list[str]:
        # links = parsed.wikicode.filter_wikilinks()
        links = extract_standalone_links(str(self.wikicode))

        res = []
        for link in links:
            title = link.title
            if "Category" in link:
                res.append(title.split(":")[-1])

        return list(set(res))
