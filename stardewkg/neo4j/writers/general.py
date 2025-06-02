from stardewkg.utils.neo4j_utils import create_relationship_neo4j
from stardewkg.definitions import SEASONS

def create_dates(driver):

    days_months = []
    
    # Date to season mapping
    for season in SEASONS:
        for day in range(1, 29):
            days_months.append(f"{season} {day}")
            create_relationship_neo4j(driver,
                                    from_node_labels="Date",
                                    from_node_name=days_months[-1],
                                    to_node_labels="Date",
                                    to_node_name=season,
                                    rel_type="PART_OF")

    # Season cyclicity
    edges = [(SEASONS[i], SEASONS[(i + 1) % len(SEASONS)])
            for i in range(len(SEASONS))]
    for edge in edges:
        create_relationship_neo4j(driver,
                                from_node_labels="Date",
                                from_node_name=edge[0],
                                to_node_labels="Date",
                                to_node_name=edge[1],
                                rel_type="PRECEED")
        create_relationship_neo4j(driver,
                                from_node_labels="Date",
                                from_node_name=edge[1],
                                to_node_labels="Date",
                                to_node_name=edge[0],
                                rel_type="FOLLOW")

    # Dates cyclicity
    edges = [(days_months[i], days_months[(i + 1) % len(days_months)])
            for i in range(len(days_months))]

    for edge in edges:
        create_relationship_neo4j(driver,
                                from_node_labels="Date",
                                from_node_name=edge[0],
                                to_node_labels="Date",
                                to_node_name=edge[1],
                                rel_type="PRECEED")
        create_relationship_neo4j(driver,
                                from_node_labels="Date",
                                from_node_name=edge[1],
                                to_node_labels="Date",
                                to_node_name=edge[0],
                                rel_type="FOLLOW")
