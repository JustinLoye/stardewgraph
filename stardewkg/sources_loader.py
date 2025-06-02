from pathlib import Path
import re
import pandas as pd
import dotenv
import os

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stardewkg.source_parser import SourceParser


from collections import defaultdict
import mwparserfromhell


def extract_standalone_links(text):
    pattern = r"^\s*(\[\[.*?\]\])\s*$"
    links = re.findall(pattern, text, flags=re.MULTILINE)
    links = [mwparserfromhell.parse(link).filter_wikilinks()[0] for link in links]
    return links


def get_categories(parsed: "SourceParser"):
    links = extract_standalone_links(str(parsed.wikicode))

    res = []
    for link in links:
        title = link.title
        if "Category" in link:
            res.append(title.split(":")[-1])

    return res


def load_sources() -> pd.DataFrame:
    dotenv.load_dotenv()

    data_folder = os.getenv("DATA_FOLDER_WIKILINKS")

    folder_path = Path(data_folder)

    # Collect file details
    file_data = []
    for f in folder_path.iterdir():
        if f.is_file() and f.suffix.lower()==".txt":
            file_data.append(
                {
                    "Filename": f.name,
                    "Size (KB)": f.stat().st_size / 1024,
                    "Created": f.stat().st_ctime,
                    "Modified": f.stat().st_mtime,
                    "Extension": f.suffix.lower(),
                }
            )

    df = pd.DataFrame(file_data)

    # Convert timestamps to readable dates
    df["Created"] = pd.to_datetime(df["Created"], unit="s")
    df["Modified"] = pd.to_datetime(df["Modified"], unit="s")

    df["Title"] = df["Filename"].apply(lambda x: x.replace(".txt", "").capitalize())
    df["Filepath"] = df["Filename"].apply(lambda x: os.path.join(data_folder, x))

    # Sort duplicates (caused by hyperlinks crawl, no prob)
    df.sort_values(by="Size (KB)", inplace=True, ascending=False)
    df.drop_duplicates(subset=["Title"], keep="first", inplace=True)

    df.set_index("Title", inplace=True)
    return df


def parse_file(df_row, parser: "SourceParser"):
    with open(df_row["Filepath"], "r") as f:
        source = f.read()

    return parser(df_row.name, source=source)


def parse_sources(df: pd.DataFrame, parser: "SourceParser"):
    df["parsed"] = df.apply(parse_file, args=[parser], axis=1)
    df.loc[:, "infobox_type"] = df["parsed"].apply(lambda x: x.infobox_type)


def add_categories(df: pd.DataFrame):
    df["categories"] = [set() for _ in range(len(df))]
    categories_count = defaultdict(int)

    for index, parsed in dict(df["parsed"]).items():
        categories = get_categories(parsed)
        for category in categories:
            categories_count[category] += 1
            df.loc[index, "categories"].add(category)
