import requests
import openai
from serpapi import GoogleSearch
import os

# API Keys (Use environment variables for security)
SERP_API_KEY = os.getenv("SERP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Step 1: Fetch Results from SERP API
print("\n🔍 Fetching results from SERP API...")

params = {
    "engine": "google",
    "q": "property24.com ,South Africa having City Johannesburg, address 17 Mystere Avenue, Impala Park, Boksburg",
    "api_key": SERP_API_KEY,
}

search = GoogleSearch(params)
results = search.get_dict()
organic_results = results.get("organic_results", [])

# Extracting links from organic_results
links = [result["link"] for result in organic_results]

if links:
    print("✅ SERP API Results:")
    for i, link in enumerate(links):
        print(f"{i + 1}. {link}")

    # Step 2: Fetch HTML Content from the first link
    link_url = links[2]
    print(f"\n🌍 Fetching HTML content from: {link_url}")
    
    response = requests.get(link_url)
    
    if response.status_code == 200:
        html_data = response.text
        print("✅ HTML content fetched successfully.")
        
        # Save the HTML content to a file
        with open("scraped.html", "w", encoding="utf-8") as file:
            file.write(html_data)
        print("📂 HTML content saved to scraped.html")
    else:
        print(f"❌ Failed to retrieve data. Status code: {response.status_code}")
        html_data = ""
else:
    print("❌ No links found.")
    html_data = ""

# Step 3: Process HTML with OpenAI API
if html_data:
    print("\n🤖 Processing HTML content with OpenAI API...")
    
    # Read the saved file content
    with open("scraped.html", "r", encoding="utf-8") as file:
        html_content = file.read()
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""
    Analyze the html_data that I provided to you. From that provide me the titles that are available in html content, title of the properties , descriptions of the properties that are in the html content , Provide prices (do not convert the price, give me same as in provided html), Provide square meters also provide me details Url.
    Provide a minimum of 10 to 20 results in structured JSON format with these keys:  
    "title", "description", "price", "square_meter","details_url".  

    HTML Content (trimmed for token limit):
    {html_content[:100000]}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert in property analysis and pricing."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )
    
    json_response = response.choices[0].message.content
    print("\n📊 OpenAI Response:\n", json_response)
else:
    print("❌ No HTML content to process.")
