import logging
import os
from stardewkg.llm_json_formatter import texts_to_json

from stardewkg.source_parser import SourceParser, get_tables, format_page_name
from stardewkg.utils.neo4j_utils import create_node_neo4j, create_relationship_neo4j
from stardewkg.utils.utils import get_parenthesis
from neo4j import Driver


def add_bundle(driver: Driver, bundle: dict):
    name = bundle["id"]

    create_node_neo4j(
        driver, labels="Bundle", name=name, properties={"reward": bundle["reward"]}
    )

    for item in bundle["bundle"]:
        link_properties = {}
        parenthesis = get_parenthesis(item)
        if parenthesis:
            item = item.replace(f"({parenthesis})", "").strip()
            try:
                link_properties["quantity"] = int(parenthesis)
            except:
                link_properties["data"] = parenthesis

        create_relationship_neo4j(
            driver,
            from_node_name=item,
            from_node_labels=None,
            to_node_name=name,
            to_node_labels="Bundle",
            rel_type="PART_OF",
            properties=link_properties,
        )


def add_bundles(driver: Driver, parsed: SourceParser):
    # Get bundle tables
    tables = get_tables(parsed.wikicode)
    tables = [str(table) for table in tables if 'Bundle" colspan="4"' in table]

    system_prompt = """I'd like you to help me filter and parse wikitables to json files.
    ANSWER ONLY IN JSON

    Follow this example:
    Input from user:

    ```
    {|class="wikitable"
    !id="Spring Crops Bundle" colspan="4" |[[File:Bundle Green.png|32px|link=]] Spring Crops Bundle
    |-
    | rowspan="4" |[[File:Spring Crops Bundle.png|center]]
    | rowspan="4" |[[File:Bundle Slot.png|center|link=]][[File:Bundle Slot.png|center|link=]][[File:Bundle Slot.png|center|link=]][[File:Bundle Slot.png|center|link=]]
    | {{Name|Parsnip}}
    | [[Spring]] [[Crops]]
    |-
    | {{Name|Green Bean}}
    | [[Spring]] [[Crops]]
    |-
    | {{Name|Cauliflower}}
    | [[Spring]] [[Crops]]
    |-
    | {{Name|Potato}}
    | [[Spring]] [[Crops]]
    |-
    | colspan="2" style="text-align: center;"|[[File:Bundle Reward.png|18px|link=]] Reward:
    | colspan="2" | {{Name|Speed-Gro|20}}
    |}
    ```

    Here is the expected output from you. I want only the json keys here ("id", "bundle", "reward"):
    {
            "id": "Spring Crops Bundle",
            "bundle": [
                "Parsnip",
                "Green Bean",
                "Cauliflower",
                "Potato"
            ],
            "reward": "Speed-Gro (20)"
    }"""

    filepath = os.path.join("./data/wiki/jsons/bundles_qwen2.5-coder:3b.json")

    bundles = texts_to_json(
        texts=tables, system_prompt=system_prompt, save_path=filepath
    )

    for bundle in bundles:
        add_bundle(driver=driver, bundle=bundle)


def parse_gifting(gifting_section: str):
    res = {}
    for line in gifting_section.splitlines():
        if line.startswith("|love"):
            res["love"] = line.split("=")[-1].split(",")
        elif line.startswith("|like"):
            res["like"] = line.split("=")[-1].split(",")
        elif line.startswith("|neutral"):
            res["neutral"] = line.split("=")[-1].split(",")
        elif line.startswith("|dislike"):
            res["dislike"] = line.split("=")[-1].split(",")
        elif line.startswith("|hate"):
            res["hate"] = line.split("=")[-1].split(",")
        else:
            pass
    return res


def add_gifting(driver: Driver, parsed: SourceParser):
    if "Gifting" not in parsed.headings:
        return

    section = parsed.get_heading_content("Gifting")
    parsed_gifting = parse_gifting(section)

    rel_type_mapping = {
        "love": "LOVES",
        "like": "LIKES",
        "neutral": "NEUTRAL",
        "dislike": "DISLIKES",
        "hate": "HATES",
    }

    for rel_type, villagers in parsed_gifting.items():
        rel_type = rel_type_mapping[rel_type]
        for villager in villagers:
            create_relationship_neo4j(
                driver,
                from_node_name=villager,
                from_node_labels="Villager",
                to_node_name=parsed.name,
                to_node_labels=None,
                rel_type=rel_type,
            )


def add_page_categories(driver: Driver, parsed: SourceParser):
    """Add the categories listed at the bottom of the page"""
    if len(parsed.categories) == 0:
        # Handle artifacts edge case (no categories in source but visible in html)
        if r"{{NavboxArtifacts}}" in str(parsed.wikicode):
            # logging.debug(f"Fix category Artifcats for {parsed.name}")
            create_relationship_neo4j(
                driver,
                from_node_name=parsed.name,
                from_node_labels=None,
                to_node_name="Artifacts",
                to_node_labels="Category",
                rel_type="PART_OF",
            )
        else:
            # logging.debug(f"Page {parsed.name} does not have any category")
            return

    for category in parsed.categories:
        create_relationship_neo4j(
            driver,
            from_node_name=parsed.name,
            from_node_labels=None,
            to_node_name=category,
            to_node_labels="Category",
            rel_type="PART_OF",
        )


def add_categories_structure(driver: Driver, category_parsed: SourceParser):
    """Add the categories listed at the bottom of the page"""

    # Get the category name
    name = format_page_name(category_parsed.name.split(":")[-1])
    if "%" in name:
        return

    # Extract parent category and add it to kg
    links = category_parsed.wikicode.filter_wikilinks()
    for link in links:
        title = link.title
        if "Category" in title:
            parent_category = title.split(":")[-1]
            create_relationship_neo4j(
                driver,
                from_node_name=name,
                from_node_labels="Category",
                to_node_name=parent_category,
                to_node_labels="Category",
                rel_type="PART_OF",
            )
