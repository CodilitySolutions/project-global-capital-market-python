# Example prompt strings stored here

GET_COST_PROMPT_TEMPLATE = """
Address: {address}, city: {city}, country: {country}
What is per meter square cost in dollar of property in this area?
Include fields: 'cost', 'address'. Do not include currency symbol in the response.
Return the JSON formatted with {{}} and don't wrap with ```json.
"""

NEIGHBORHOOD_PROMPT_TEMPLATE = """
{full_address}
In which neighborhood is this street located?
Provide response in {{'address': neighborhood_address}} format only.
Return the JSON formatted with {{}} and don't wrap with ```json.
Neighborhood should not contain single quotes or apostrophes.
If not found, return {{'address': '', 'error': error}}.
"""

# Add other large reusable prompts here as needed
