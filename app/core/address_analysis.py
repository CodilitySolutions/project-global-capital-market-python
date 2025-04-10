import json
from app.openai_utils.assistant_client import client
from app.settings.config import CHATGPT_MODEL

async def get_cost(neighborhood_address, city, country):
    cost_prompt = "Address: "+neighborhood_address+", city: "+city+", country: "+country+"\nWhat is per meter square cost in dollar of property in this area?\nInclude fields: 'cost', 'address'. Do not include currency symbol in the response.\nReturn the JSON formatted with {} and don't wrap with ```json."

    response = await get_openai_response(cost_prompt)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            print('response: ', response)
        except:
            response = {"cost": 0}

    cost = response.get("cost", 0)
    try:
        return float(cost)
    except:
        return 0

async def get_average_cost(full_address):
    average_cost_prompt = full_address+"\n\nWhat is the average per meter square cost in dollar of property in this area?\nInclude fields: 'cost', 'address'. Do not include currency symbol in the response.\nReturn the JSON formatted with {} and don't wrap with ```json."

    response = await get_openai_response(average_cost_prompt)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            print('response: ', response)
        except:
            response = {"cost": 0}

    average_cost = response.get("cost", 0)
    try:
        return float(average_cost)
    except:
        return 0

async def get_neighbourhood_address(full_address):
    neighborhood_prompt = full_address+"\n\nIn which neighborhood is this street located?\nProvide response in {'address': neighborhood_address} format only.\nReturn the JSON formatted with {} and don't wrap with ```json.\nNeighborhood should not contains single quote and apostrophe s.\n If neighborhood not found than {'address': '', 'error': error}. Not include unknown or not available in response."

    response = await get_openai_response(neighborhood_prompt)
    print('get_neighbourhood_address response: ', response)
    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            # print('response: ', response)
        except:
            response = {"address": ""}

    return response.get("address", "")

async def analyse_address_using_openai(address):
    response = {'object': '', 'area_type': '', 'street_people_type': '', 'property_type': '', 'people_type': '', 'neighbourhood_people_type': ''}

    response = await client.chat.completions.create(
        model=CHATGPT_MODEL,
        temperature=0,
    messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Address: "+address+"\nGive me response in this json format: {'area_type': 'commercial or residential', 'street_people_type': 'which type of peoples are living in the street like Wealthy, Upper Class, Mid Class, Low Class', 'property_type': 'type of property in that area like luxurius home, raw house etc', 'people_type': 'which type of people are living in this address like Wealthy, Upper Class, Mid Class, Low Class', 'neighbourhood_people_type': 'which type of people are living in the neighbourhood like Wealthy, Upper Class, Mid Class, Low Class'}\nReturn the JSON formatted with {} and don't wrap with ```json.",
                    }
                ],
            }
        ],
    )
    response = response.choices[0].message.content

    if type(response) != "json":
        try:
            response = json.loads(response.replace("'", "\""))
            print('address analyse: ', response)
        except:
            pass

    return response
