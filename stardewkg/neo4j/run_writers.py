import mwparserfromhell
import os
import dotenv
from tqdm import tqdm
from neo4j import Driver
from stardewkg.llm_json_formatter import infoboxes_to_json
from stardewkg.source_parser import SourceParser
from stardewkg.utils.utils import category_to_neo4j, format_page_name
from stardewkg.sources_loader import load_sources, parse_sources, add_categories
from stardewkg.neo4j.writers.body import (
    add_bundles,
    add_gifting,
    add_page_categories,
    add_categories_structure,
)
from stardewkg.utils.neo4j_utils import get_neo4j_driver, make_query
from stardewkg.neo4j.writers.general import create_dates
import logging
import sys
from stardewkg.neo4j.writers.infobox import (
    AnimalWriter,
    ArtifactWriter,
    BuildingWriter,
    CropWriter,
    FishWriter,
    FurnitureWriter,
    InfoboxWriter,
    LocationWriter,
    MonsterWriter,
    SeedWriter,
    ToolWriter,
    TreeWriter,
    VillagerWriter,
    WeaponWriter,
)

# python -m stardewkg.neo4j.run_writers

# Set up logging
FORMAT = "%(asctime)s %(levelname)s %(message)s"
filepath = "logs/run_writers.log"
logging.basicConfig(
    handlers=[logging.FileHandler(filepath), logging.StreamHandler(sys.stdout)],
    level=logging.INFO,
    format=FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)
logging.info(f"Logging to {filepath}")

# Set up neo4j
dotenv.load_dotenv()
driver: Driver = get_neo4j_driver()

# Part where I dont need any data (definitions)
logging.info("Adding dates")
create_dates(driver=driver)

# Load data
logging.info("Loading wikilinks files")
df = load_sources()
logging.info("Parsing the sources")
parse_sources(df, SourceParser)
logging.info("Getting pages categories")
add_categories(df)

# Infobox part

infoboxes = [(parsed.name, str(parsed.infobox)) for parsed in df["parsed"].values]

filepath = os.path.join("./data/wiki/jsons/infoboxes_qwen2.5-coder:3b.json")

infoboxes = infoboxes_to_json(infoboxes=infoboxes, save_path=filepath)


# Add nodes fully refactored by InfoboxWriter
for infobox_type in ["Clothing", "Mineral", "Cooking"]:
    logging.info(f"Adding nodes with label {infobox_type}")
    pages = df.loc[df["infobox_type"] == infobox_type.lower()].index.tolist()
    for page in pages:
        name = format_page_name(page)
        data = infoboxes[page.replace("_", " ")]
        if data:
            InfoboxWriter(driver, name, data, labels=infobox_type).write()

# Add nodes who need to have extended InfoboxWriter
infobox_type2writer = {
    "Villager": VillagerWriter,
    "Location": LocationWriter,
    "Fish": FishWriter,
    "Monster": MonsterWriter,
    "Furniture": FurnitureWriter,
    "Animal": AnimalWriter,
    "Tool": ToolWriter,
    "Tree": TreeWriter,
    "Building": BuildingWriter,
    "Artifact": ArtifactWriter,
    "Seed": SeedWriter,
    "Weapon": WeaponWriter,
}

for infobox_type, writer in infobox_type2writer.items():
    logging.info(f"Adding nodes with label {infobox_type}")
    pages = df.loc[df["infobox_type"] == infobox_type.lower()].index.tolist()
    for page in pages:
        name = format_page_name(page)
        data = infoboxes[page.replace("_", " ")]
        if data:
            writer(driver, name, data, labels=infobox_type).write()

# Add infobox without type but with
#   - an interesting category
#   - a constant infobox field pattern within the category
# I will be playing with categories so let's add them first to the KG

logging.info("Adding page to category mapping")
for parsed in tqdm(
    df["parsed"].values, total=len(df), desc="page to category processing"
):
    add_page_categories(driver, parsed)

logging.info("Adding category structure")
mask = df["Filename"].apply(lambda x: "Category" in x)
for parsed in df.loc[mask, "parsed"].values:
    add_categories_structure(driver, parsed)

# Lets work on the crops.
# I need to remove the seeds because they are already added to the KG(known infoboxes)
query = """MATCH (top:Category {name: "Crops"})
MATCH (leaf:Category)-[r:PART_OF*]->(top)
WHERE NOT (leaf)<-[:PART_OF]-()
RETURN DISTINCT leaf.name"""
records, summary, keys = driver.execute_query(query)
subcrops = set(
    [
        record.value().replace("_", " ")
        for record in records
        if "seed" not in record.value()
    ]
)
subcrop_mask = df["categories"].apply(lambda x: bool(x & subcrops))
crops = df.loc[subcrop_mask].index.to_list()

for crop in crops:
    name = format_page_name(crop)
    data = infoboxes[crop.replace("_", " ")]
    if data:
        CropWriter(driver, name, data).write()


# Now let's add populated categories with a generic InfoboxWriter
categories = [
    "Craftable items",
    "Special items",
    "Artisan Goods",
    "Books",
    "Resources",
    "Animal Products",
    "Decor",
    "Craftable lighting",
    "Fishing Tackle",
    "Field Office donations",
]

for category in categories:
    mask = df.apply(
        lambda x: x["infobox_type"] == "unknown" and bool(x["categories"] & {category}),
        axis=1,
    )
    pages = df.loc[mask].index.to_list()
    for page in pages:
        name = format_page_name(page)
        data = infoboxes[page.replace("_", " ")]
        if data:
            InfoboxWriter(
                driver, name, data, labels=category_to_neo4j(category)
            ).write()


# Body part

logging.info("Adding Bundles")
add_bundles(driver, df.loc["Bundles", "parsed"])

logging.info("Adding Giftings")
for parsed in tqdm(df["parsed"].values, total=len(df)):
    add_gifting(driver, parsed)


# Cleaning up
with driver.session() as session:
    
    # Remove duplicates (2 nodes)
    query = """MATCH (n)
    WITH n.name AS name, collect(n) AS nodes
    WHERE size(nodes) > 1
    WITH nodes[0] AS nodeToDelete
    DETACH DELETE nodeToDelete"""
    records, summary, keys = session.execute_query(driver, query)


    # For each label, create a UNIQUE constraint on `name`
    labels = make_query("CALL db.labels() YIELD label RETURN label").value()
    for label in labels:
        query = f"""
        CREATE CONSTRAINT IF NOT EXISTS unique_{label}_name
        FOR (n:`{label}`)
        REQUIRE n.name IS UNIQUE;
        """
        session.execute_query(query)


logging.info("Knowledge graph construction is done")
