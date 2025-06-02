import logging

from stardewkg.utils.neo4j_utils import create_node_neo4j, create_relationship_neo4j
from stardewkg.utils.utils import get_parenthesis, remove_parenthesis
from stardewkg.definitions import SEASONS, SKILLS, VILLAGERS

from neo4j.exceptions import CypherTypeError

import mwparserfromhell


def handle_location(driver, node_name: str, location: str, node_labels=["Item"]):
    # Parenthesis for locations are quite general, so I store them in data
    parenthesis = get_parenthesis(location)
    link_properties = {}
    if parenthesis:
        link_properties["data"] = parenthesis
        location = remove_parenthesis(location)

    create_relationship_neo4j(
        driver,
        from_node_labels=node_labels,
        from_node_name=node_name,
        to_node_labels="Location",
        to_node_name=location,
        rel_type="LIVES_IN",
    )


def handle_ingredient(driver, node_name: str, ingredient: str, node_labels=["Item"]):
    # Parenthesis for ingredients are generally quantity or general data
    parenthesis = get_parenthesis(ingredient)
    link_properties = {}
    if parenthesis:
        try:
            link_properties = {"quantity": int(parenthesis)}
        except ValueError:
            if "any" in parenthesis.lower():
                link_properties = {"quantity": "Any"}
            else:
                link_properties = {"data": parenthesis}
        ingredient = remove_parenthesis(ingredient, parenthesis)

    create_relationship_neo4j(
        driver,
        from_node_labels=node_labels,
        from_node_name=node_name,
        to_node_labels=None,
        to_node_name=ingredient,
        rel_type="REQUIRES",
        properties=link_properties,
    )


def handle_source(driver, node_name: str, source: str, node_labels=["Item"]):
    link_properties = {}
    parenthesis = get_parenthesis(source)
    if parenthesis:
        link_properties["data"] = parenthesis

    if "Fishing" in source and "Treasure" in source:
        create_relationship_neo4j(
            driver,
            from_node_labels=node_labels,
            from_node_name=node_name,
            to_node_labels="Skill",
            to_node_name="Fishing",
            rel_type="SOURCE",
        )

        if "Golden" in source:
            create_relationship_neo4j(
                driver,
                from_node_labels=node_labels,
                from_node_name=node_name,
                to_node_labels="SpecialItem",
                to_node_name="Golden Fishing Treasure Chest",
                rel_type="SOURCE",
                properties=link_properties,
            )
        else:
            create_relationship_neo4j(
                driver,
                from_node_labels=node_labels,
                from_node_name=node_name,
                to_node_labels="SpecialItem",
                to_node_name="Fishing Treasure Chest",
                rel_type="SOURCE",
                properties=link_properties,
            )

    elif "Crafting" in source:
        create_relationship_neo4j(
            driver,
            from_node_labels=node_labels,
            from_node_name=node_name,
            to_node_labels=None,
            to_node_name="Crafting",
            rel_type="SOURCE",
            properties=link_properties,
        )

    elif "Desert Festival" in source:
        create_relationship_neo4j(
            driver,
            from_node_labels=node_labels,
            from_node_name=node_name,
            to_node_labels="Event",
            to_node_name="Desert Festival",
            rel_type="SOURCE",
            properties=link_properties,
        )

    else:
        source = remove_parenthesis(source)
        create_relationship_neo4j(
            driver,
            from_node_labels=node_labels,
            from_node_name=node_name,
            to_node_labels=None,
            to_node_name=source,
            rel_type="SOURCE",
            properties=link_properties,
        )


def handle_recipe(driver, node_name: str, recipe: str, node_labels=["Item"]):
    # Handle Queen of Sauce source (Cooking node)
    for season in SEASONS:
        if season in recipe:
            day_month = recipe.split(",")[0]
            year = int(recipe[-1])

            create_relationship_neo4j(
                driver,
                from_node_labels=["Cooking"],
                from_node_name=node_name,
                to_node_labels=["Date"],
                to_node_name=day_month,
                rel_type="RECIPE_SOURCE",
                properties={"year": year},
            )
            return

    # Handle from Skill source
    for skill in SKILLS:
        if skill in recipe:
            # Parenthesis is generally skill level
            link_properties = {}
            parenthesis = get_parenthesis(recipe)
            if parenthesis:
                try:
                    link_properties = {"level": int(parenthesis)}
                except ValueError:
                    link_properties = {"data": parenthesis}

            create_relationship_neo4j(
                driver,
                from_node_labels=node_labels,
                from_node_name=node_name,
                to_node_labels=["Skill"],
                to_node_name=skill,
                rel_type="RECIPE_SOURCE",
                properties=link_properties,
            )
            return

    # Handle from Villager friendship
    for villager in VILLAGERS:
        villager.replace("_", " ")
        if villager in recipe:
            link_properties = {}
            parenthesis = get_parenthesis(recipe)
            if parenthesis:
                link_properties = {"data": parenthesis}
            create_relationship_neo4j(
                driver,
                from_node_labels=node_labels,
                from_node_name=node_name,
                to_node_labels=["Villager"],
                to_node_name=villager,
                rel_type="RECIPE_SOURCE",
                properties=link_properties,
            )
            return


def handle_season(driver, node_name: str, season: str, node_labels=["Item"]):
    link_properties = {}
    parenthesis = get_parenthesis(season)
    link_properties = {}
    if parenthesis:
        link_properties["data"] = parenthesis
        season = remove_parenthesis(season)

    create_relationship_neo4j(
        driver,
        from_node_labels=node_labels,
        from_node_name=node_name,
        to_node_labels="Date",
        to_node_name=season,
        rel_type="AVAILABLE_IN",
        properties=link_properties,
    )


def handle_buff(driver, node_name: str, buff: str, node_labels=["Item"]):
    buff_value = get_parenthesis(buff)
    if buff_value:
        link_properties = {"value": buff_value}
        buff_type = remove_parenthesis(buff)
    else:
        link_properties = {}
        buff_type = buff

    if buff_type in SKILLS:
        to_node_labels = "Skill"
    else:
        to_node_labels = "Buff"

    create_relationship_neo4j(
        driver,
        from_node_labels=node_labels,
        from_node_name=node_name,
        to_node_labels=to_node_labels,
        to_node_name=buff_type,
        rel_type="BUFF",
        properties=link_properties,
    )


def handle_product(driver, node_name: str, product: str, node_labels=["Item"]):
    create_relationship_neo4j(
        driver,
        from_node_labels=node_labels,
        from_node_name=node_name,
        to_node_labels=None,
        to_node_name=product,
        rel_type="PRODUCES",
    )


def handle_xp(driver, node_name: str, xp: str, node_labels=["Item"]):
    for skill in SKILLS:
        if skill in xp:
            link_properties = {"data": xp}
            create_relationship_neo4j(
                driver=driver,
                from_node_labels=node_labels,
                from_node_name=node_name,
                to_node_labels="Skill",
                to_node_name=skill,
                rel_type="XP",
                properties=link_properties,
            )


# os, price, produce


class InfoboxWriter:
    """Base class for parsing infoboxes and creating knowledge graph nodes/relationships."""

    def __init__(self, driver, name: str, data: dict, labels=["Item"]):
        self.driver = driver
        self.name = name  # Node name
        self.data = data  # Infobox data
        self.labels = labels  # Node labels
        self.properties = {}

        # Register common field handlers used across multiple infobox types
        self.common_handlers = {
            "location": self._handle_location,
            "ingredients": self._handle_ingredient,
            "tingredients": self._handle_ingredient,
            "source": self._handle_source,
            "recipe": self._handle_recipe,
            "season": self._handle_season,
            "buff": self._handle_buff,
            "stats": self._handle_buff,
            "produce": self._handle_product,
            "produces": self._handle_product,
            "xp": self._handle_xp,
        }
        # Additional handlers specific to this infobox type (to be overridden by subclasses)
        self.specific_handlers = {}

    def write(self):
        """
        Process infobox data into nodes and relationships.
        """
        logging.debug(f"Parsing {self.name} ({self.labels})")

        # Combine common and specific handlers, with specific ones taking precedence
        all_handlers = {**self.common_handlers, **self.specific_handlers}

        for key, val in self.data.items():
            if key in all_handlers:
                try:
                    # Get the appropriate handler
                    handler = all_handlers[key]
                    # Ensure we're working with a list
                    entities = (
                        [val] if isinstance(val, str) or isinstance(val, int) else val
                    )
                    # print(self.name, entities)
                    # Apply handler to each item
                    for entity in entities:
                        if str(entity) == "N/A" or str(entity).lower == "none":
                            continue
                        handler(entity)

                except CypherTypeError:
                    print(self.name, key, entity)
                    raise CypherTypeError
            else:
                # Store as a regular property
                self.properties[key] = val

        try:
            self._create_node(self.name, self.properties)
        except CypherTypeError:
            print(self.name, key, entity)
        self._postprocess()

    def _create_node(self, name, properties):
        """Create the main node for this infobox."""
        create_node_neo4j(
            self.driver, labels=self.labels, name=name, properties=properties
        )

    def _postprocess(self):
        pass

    # Common field handlers
    def _handle_ingredient(self, ingredient):
        """Handle ingredient relationships."""
        handle_ingredient(self.driver, self.name, ingredient, node_labels=self.labels)

    def _handle_source(self, source):
        """Handle source relationships."""
        handle_source(self.driver, self.name, source, node_labels=self.labels)

    def _handle_recipe(self, recipe):
        """Handle recipe relationships."""
        handle_recipe(self.driver, self.name, recipe, node_labels=self.labels)

    def _handle_location(self, location):
        handle_location(self.driver, self.name, location, node_labels=self.labels)

    def _handle_season(self, season):
        handle_season(self.driver, self.name, season, node_labels=self.labels)

    def _handle_buff(self, buff):
        handle_buff(self.driver, self.name, buff, node_labels=self.labels)

    def _handle_product(self, product):
        handle_product(self.driver, self.name, product, node_labels=self.labels)

    def _handle_xp(self, xp):
        handle_xp(self.driver, self.name, xp, node_labels=self.labels)


class VillagerWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Villager"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "address": self._handle_address,
            "family": self._handle_family,
            "friends": self._handle_friend,
            "birthday": self._handle_birthday,
            "favorites": self._handle_favorite,
        }

    def _handle_address(self, val):
        # Remove unwanted parenthesis like "Carpenter's Shop (24 Mountain Road)"
        val = remove_parenthesis(val)
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Villager",
            from_node_name=self.name,
            to_node_labels="Location",
            to_node_name=val,
            rel_type="LIVES_IN",
        )

    def _handle_family(self, val):
        link_properties = {}
        rel_type = get_parenthesis(val)
        if rel_type:
            link_properties["type"] = rel_type
            val = remove_parenthesis(val)

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Villager",
            from_node_name=self.name,
            to_node_labels="Villager",
            to_node_name=val,
            rel_type="HAS_FAMILY_MEMBER",
            properties=link_properties,
        )

    def _handle_friend(self, val):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Villager",
            from_node_name=self.name,
            to_node_labels="Villager",
            to_node_name=val,
            rel_type="FRIENDS_WITH",
        )

    def _handle_birthday(self, val):
        val = val.replace("(", "").replace(")", "")
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Villager",
            from_node_name=self.name,
            to_node_labels="Date",
            to_node_name=val,
            rel_type="BIRTHDAY",
        )

    def _handle_favorite(self, val):
        """I dont use this info"""
        pass


class LocationWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Location"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {"occupants": self._handle_occupant}

    def _handle_occupant(self, val):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Location",
            from_node_name=self.name,
            to_node_labels="Villager",
            to_node_name=val,
            rel_type="HAS_OCCUPANT",
        )


class FishWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Fish"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "weather": self._handle_weather,
            "size": self._handle_size,
        }
        self.properties["size"] = []

    def _handle_weather(self, val):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Fish",
            from_node_name=self.name,
            to_node_labels="Weather",
            to_node_name=val,
            rel_type="AVAILABLE_IN",
        )

    def _handle_size(self, val):
        self.properties["size"].append(val)

    def _postprocess(self):
        """fix sizes"""
        props = self.properties
        size = props.get("size")

        if not size:
            return

        if len(size) == 1:
            new_size = str(size[0])
        elif len(size) == 2:
            a, b = size
            new_size = f"{a}-{b}"
        else:
            props.pop("size")
            return

        props["size"] = new_size

        return


class MonsterWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Monster"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "drops": self._handle_drop,
            "variations": self._handle_variation,
        }

    def _handle_drop(self, drop):
        link_properties = {}
        parenthesis = get_parenthesis(drop)
        if parenthesis:
            link_properties = {"data": parenthesis}
            drop = remove_parenthesis(drop)

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Monster",
            from_node_name=self.name,
            to_node_labels=None,
            to_node_name=drop,
            rel_type="DROP",
            properties=link_properties,
        )

    def _handle_variation(self, variation):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Monster",
            from_node_name=self.name,
            to_node_labels="Monster",
            to_node_name=variation,
            rel_type="VARIANT",
        )


class FurnitureWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Furniture"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "os": self._handle_os,
        }

    def _handle_os(self, source):
        parenthesis = get_parenthesis(source)
        link_properties = {}
        if parenthesis:
            link_properties = {"data": parenthesis}
            source = remove_parenthesis(source)

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Furniture",
            from_node_name=self.name,
            to_node_labels=None,
            to_node_name=source,
            rel_type="SOURCE",
            properties=link_properties,
        )


class AnimalWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Animal"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {"building": self._handle_building}

    def _handle_building(self, building):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Animal",
            from_node_name=self.name,
            to_node_labels="Building",
            to_node_name=building,
            rel_type="LIVES_IN",
        )


class ToolWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Tool"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "previoustier": self._handle_previoustier,
            "nexttier": self._handle_nexttier,
            "soldby": self._handle_source,  # SOURCE to avoid link type proliferation
        }

    def _handle_previoustier(self, previoustier):
        if previoustier == "N/A":
            return
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Tool",
            from_node_name=self.name,
            to_node_labels="Tool",
            to_node_name=previoustier,
            rel_type="PREVIOUS_TIER",
        )

    def _handle_nexttier(self, nexttier):
        if nexttier == "N/A":
            return
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Tool",
            from_node_name=self.name,
            to_node_labels="Tool",
            to_node_name=nexttier,
            rel_type="NEXT_TIER",
        )


class TreeWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Tree"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "seed": self._handle_seed,
            "tapper": self._handle_tapper,
            "sapling": self._handle_sapling,
            "produce": self._handle_produce,
            "season": self._handle_season,
            "altprice": self._handle_source,
        }

    def _handle_seed(self, seed):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Tree",
            from_node_name=self.name,
            to_node_labels="Seed",
            to_node_name=seed,
            rel_type="SOURCE",
        )

    def _handle_tapper(self, product):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Tree",
            from_node_name=self.name,
            to_node_labels=None,
            to_node_name=product,
            rel_type="PRODUCES",
        )

    def _handle_sapling(self, sapling):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Tree",
            from_node_name=self.name,
            to_node_labels="Seed",
            to_node_name=sapling,
            rel_type="SOURCE",
        )

    def _handle_produce(self, fruit):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Tree",
            from_node_name=self.name,
            to_node_labels="Fruit",
            to_node_name=fruit,
            rel_type="PRODUCES",
        )

    def _handle_season(self, season):
        # Handle parenthesis for tree growing in different seasons at different places
        link_properties = {}
        parenthesis = get_parenthesis(season)
        if parenthesis:
            season = remove_parenthesis(season)
            link_properties["location"] = parenthesis

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Tree",
            from_node_name=self.name,
            to_node_labels="Date",
            to_node_name=season,
            rel_type="AVAILABLE_IN",
            properties=link_properties,
        )


class BuildingWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Building"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "materials": self._handle_material,
            "animals": self._handle_animal,
        }

    def _handle_material(self, material):
        # Handle quantity given in parenthesis
        link_properties = {}
        quantity = get_parenthesis(material)
        if quantity:
            material = remove_parenthesis(material)
            link_properties["quantity"] = quantity

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Building",
            from_node_name=self.name,
            to_node_labels=None,
            to_node_name=material,
            rel_type="REQUIRES",
            properties=link_properties,
        )

    def _handle_animal(self, animal):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Building",
            from_node_name=self.name,
            to_node_labels="Animal",
            to_node_name=animal,
            rel_type="HAS_OCCUPANT",
        )


class ArtifactWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Artifact"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {
            "as": self._handle_as,
            "os": self._handle_os,
            "dr": self._handle_dr,
            "md": self._handle_md,
        }

    def _handle_as(self, source):
        link_properties = {}
        proba = get_parenthesis(source)
        if proba:
            source = source.replace(f"({proba})", "").strip()
            link_properties["probability"] = proba

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Artifact",
            from_node_name=self.name,
            to_node_labels="Location",
            to_node_name=source,
            rel_type="SOURCE",
            properties=link_properties,
        )

    def _handle_os(self, source):
        """dont try this at home"""
        link_properties = {}
        parenthesis = get_parenthesis(source)

        if parenthesis:
            second_parenthesis = get_parenthesis(parenthesis)
            if second_parenthesis:
                # print("nested")
                # print(name, source, parenthesis, second_parenthesis)
                link_properties["probability"] = second_parenthesis
                parenthesis = parenthesis.replace(f"({parenthesis})", "").strip()

            # 2 cases: probabibility or hyperlink
            # Check if hyperlinks
            wikicode = mwparserfromhell.parse(parenthesis)
            links = wikicode.filter_wikilinks()
            if links:
                for link in links:
                    link = link.replace("[", "").replace("]", "")
                    create_relationship_neo4j(
                        self.driver,
                        from_node_labels="Artifact",
                        from_node_name=self.name,
                        to_node_labels=None,
                        to_node_name=link,
                        rel_type="SOURCE",
                        properties=link_properties,
                    )
            else:
                link_properties["probability"] = parenthesis
                source = remove_parenthesis(source)
                create_relationship_neo4j(
                    self.driver,
                    from_node_labels="Artifact",
                    from_node_name=self.name,
                    to_node_labels=None,
                    to_node_name=source,
                    rel_type="SOURCE",
                    properties=link_properties,
                )

        else:
            create_relationship_neo4j(
                self.driver,
                from_node_labels="Artifact",
                from_node_name=self.name,
                to_node_labels=None,
                to_node_name=source,
                rel_type="SOURCE",
                properties=link_properties,
            )

    def _handle_dr(self, dr):
        parenthesis = get_parenthesis(dr)
        link_properties = {}
        if parenthesis:
            link_properties["quantity"] = parenthesis
            dr = remove_parenthesis(dr)

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Artifact",
            from_node_name=self.name,
            to_node_labels=None,
            to_node_name=dr,
            rel_type="REWARDS",
            properties=link_properties,
        )

    def _handle_md(self, monster):
        parenthesis = get_parenthesis(monster)
        link_properties = {}
        if parenthesis:
            link_properties["probability"] = parenthesis
            monster = remove_parenthesis(monster)

        create_relationship_neo4j(
            self.driver,
            from_node_labels="Artifact",
            from_node_name=self.name,
            to_node_labels="Monster",
            to_node_name=monster,
            rel_type="SOURCE",
            properties=link_properties,
        )


class SeedWriter(InfoboxWriter):
    def __init__(self, driver, name: str, data: dict, labels=["Seed"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {"crop": self._handle_crop}

    def _handle_crop(self, crop):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Seed",
            from_node_name=self.name,
            to_node_labels="Crop",
            to_node_name=crop,
            rel_type="PRODUCES",
        )


class WeaponWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Weapon"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {"source": self._handle_source}

    def _handle_source(self, source):
        wikicode = mwparserfromhell.parse(source)
        links = wikicode.filter_wikilinks()

        # Case one: there is a wikilink (link and store additional data)
        if len(links) == 1:
            source = links[0][2:-2]
            create_relationship_neo4j(
                self.driver,
                from_node_labels="Weapon",
                from_node_name=self.name,
                to_node_labels=None,
                to_node_name=source,
                rel_type="SOURCE",
                properties={"data": source},
            )

        elif "Adventurer's Guild" in source:
            create_relationship_neo4j(
                self.driver,
                from_node_labels="Weapon",
                from_node_name=self.name,
                to_node_labels="Location",
                to_node_name="Adventurer's Guild",
                rel_type="SOURCE",
                properties={"data": source},
            )

        elif "The Mines" in source:
            create_relationship_neo4j(
                self.driver,
                from_node_labels="Weapon",
                from_node_name=self.name,
                to_node_labels="Location",
                to_node_name="The Mines",
                rel_type="SOURCE",
                properties={"data": source},
            )

        elif "Volcano Dungeon" in source:
            create_relationship_neo4j(
                self.driver,
                from_node_labels="Weapon",
                from_node_name=self.name,
                to_node_labels="Location",
                to_node_name="Volcano Dungeon",
                rel_type="SOURCE",
                properties={"data": source},
            )

        elif "Volcano Cavern" in source:
            create_relationship_neo4j(
                self.driver,
                from_node_labels="Weapon",
                from_node_name=self.name,
                to_node_labels="Location",
                to_node_name="Volcano Cavern",
                rel_type="SOURCE",
                properties={"data": source},
            )

        elif "Desert Festival" in source:
            create_relationship_neo4j(
                self.driver,
                from_node_labels="Weapon",
                from_node_name=self.name,
                to_node_labels="Event",
                to_node_name="Desert Festival",
                rel_type="SOURCE",
                properties={"data": source},
            )

        else:
            parenthesis = get_parenthesis(source)
            link_properties = {}
            if parenthesis:
                link_properties["data"] = parenthesis
                source = remove_parenthesis(source)

            create_relationship_neo4j(
                self.driver,
                from_node_labels="Weapon",
                from_node_name=self.name,
                to_node_labels=None,
                to_node_name=source,
                rel_type="SOURCE",
                properties=link_properties,
            )
        return


class CropWriter(InfoboxWriter):
    def __init__(self, driver, name, data, labels=["Crop"]):
        super().__init__(driver, name, data, labels)

        self.specific_handlers = {"seed": self._handle_seed}

    def _handle_seed(self, seed):
        create_relationship_neo4j(
            self.driver,
            from_node_labels="Seed",
            from_node_name=seed,
            to_node_labels="Crop",
            to_node_name=self.name,
            rel_type="PRODUCES",
        )