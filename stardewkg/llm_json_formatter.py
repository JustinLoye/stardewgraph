import os
import json
import joblib
from tqdm import tqdm
import ollama
import logging


def query_ollama(text, system_prompt, model="qwen2.5-coder:3b", temperature=0.0):
    messages = [
         {"role": "system", "content": system_prompt},
          {"role": "user", "content": text}
         ]
    response = ollama.chat(model=model, messages=messages, options={
        "temperature": temperature})
    response_text = response.get("message", {}).get("content", "")
    
    return response_text


def infoboxes_to_json(infoboxes: list[str], save_path: str, model="qwen2.5-coder:3b", ** kwargs):
    """
    Convert a list of infoboxes to json with a caching mechanism
    kwargs are passed to ollama.chat option
    """
    
    # Skip if already processed
    if os.path.exists(save_path):
        logging.info("Data has already been processed by LLM, loading it")
        with open(save_path, "r") as f:
            processed = json.load(f)
        return processed
    
    system_prompt = """
    Convert the following MediaWiki infobox text to a JSON format.
    Follow these rules:
    - Remove all MediaWiki template markers ({{, }})
    - Remove MediaWiki link markers ([[ and ]])
    - Remove HTML tags
    - Convert templates like "{{template_type|template_name}}" to just the second part "template_name".
    - Add templates parameters in parenthesis: "{{NPC|Sebastian|Half-Brother}}" -> "Sebastian (Half-Brother)"
    - Be careful that some MediaWiki links and templates might be nested.
    - If some fields have an enumeration of values, group the values in a list
    - Your answer should be ONLY the formatted JSON
    Here is an example:
    Question:
    <onlyinclude>{{{{1|Infobox cooking}}
    |name = Complete Breakfast
    |image = Complete Breakfast.png
    |description = {{Description|Complete Breakfast}}
    |buff = {{Name|Farming|+2}}{{Name|Max Energy|+50}}
    |duration = 7m
    |dsvduration = 0700
    |edibility = 80
    |sellprice = 350
    |recipe = {{CookingChannel|21 Spring, Year 2}}
    |ingredients = {{Name|Fried Egg|1}}{{Name|Milk|1}}{{Name|Hashbrowns|1}}{{Name|Pancakes|1}}
    |location = The Desert{{!}}The Calico Desert
    }}</onlyinclude>
    Answer:
    {
    "name": "Complete Breakfast",
    "image": "Complete Breakfast.png",
    "description": "Complete Breakfast",
    "buff": ["Farming (2)", "Max Energy (+50)"],
    "duration": "7m",
    "dsvduration": "0700",
    "edibility": 80,
    "sellprice": 350,
    "recipe": "21 Spring, Year 2",
    "ingredients": ["Fried Egg (1)", "Milk (1)", "Hashbrowns (1)", "Pancakes (1)"],
    "location": ["The Desert", "The Calico Desert"]
    }
    """

    # Load cache if it exists
    cache_file = save_path.replace(".json", ".joblib")
    if os.path.exists(cache_file):
        logging.info("Found partially computed json")
        processed = joblib.load(cache_file)
    else:
        processed = {}

    # Loop over all infoboxes with a retry mechanism
    try:
        for (name, infobox) in tqdm(infoboxes, desc="Processing infoboxes"):
            # If already processed, skip it
            if name in processed:
                continue
            
            for attempt in range(5):
                try:
                    result = query_ollama(infobox, system_prompt, model=model, **kwargs)
                    break
                except:
                    pass
            processed[name] = result

            # Save progress after each successful parse
            joblib.dump(processed, cache_file)
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user. Progress saved to cache.")
        joblib.dump(processed, cache_file)
        exit()

    # Once all are processed, write the full result to a JSON file.
    with open(save_path, "w") as f:
        json.dump(processed, f, indent=2)
        
    return processed


def text_to_json(text: str, system_prompt: str, model="qwen2.5-coder:3b", **kwargs):
    """
    Convert a text to json
    kwargs are passed to ollama.chat option
    """

    for attempt in range(5):
        try:
            result = query_ollama(
                text, system_prompt, model=model, **kwargs)

            # Remove optional LLM formatting
            if "```json" in result:
                result = result.replace("```json", "").lstrip()
                result = result.replace("```", "").rstrip()

            # Allow to make sure LLM returned a json output
            result = json.loads(result)
            break
        except:
            pass

    return result


def texts_to_json(texts: list[str], system_prompt: str, save_path: str, model="qwen2.5-coder:3b", use_cache=True, **kwargs):
    """
    Convert a list of texts to json with a caching mechanism
    kwargs are passed to ollama.chat option
    """

    # Skip if already processed
    if os.path.exists(save_path) and use_cache:
        logging.info("Data has already been processed, loading it")
        with open(save_path, "r") as f:
            processed = json.load(f)
        return processed

    processed = []

    for text in tqdm(texts, desc="Processing texts"):

        processed.append(text_to_json(text, system_prompt, model, **kwargs))
    
    
    # Once all are processed, write the full result to a JSON file.
    with open(save_path, "w") as f:
        json.dump(processed, f, indent=2)

    return processed
