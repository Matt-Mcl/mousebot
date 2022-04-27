from gazpacho import get, Soup
import pymongo

mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_titles = mousebot_db['titles']
enums = mousebot_db['enums']
shop_items = mousebot_db['shop_items']

# Empty databases
mousebot_titles.delete_many({})
enums.delete_many({})
shop_items.delete_many({})

# Scrape Titles

url = "https://transformice.fandom.com/wiki/Title"
html = get(url)
soup = Soup(html)


def parse(table, title_type, offset=0):
    for item in table.find("tr")[offset+1:]:
        cheese = int(item.find("td")[-2].text.replace(" ", ""))
        title1 = item.find("td")[-4].text.replace("\xa0", " ")
        title2 = item.find("td")[-5].text
        titles = [title1]
        if len(title2) > 3:
            titles.append(title2)
        mousebot_titles.insert_one({"type": title_type, "titles": titles, "number": cheese})

parse(soup.find("table", {"id": "tableCheeseTotal"}), "cheese_total", 1)
parse(soup.find("table", {"id": "tableCheeseFirst"}), "cheese_first")
parse(soup.find("table", {"id": "tableCheeseBootcamp"}), "bootcamp")
# parse(soup.find("table", {"id": "tableShop"}), "shop")

parse(soup.find("table", {"id": "tableShamanNormal"})[0], "normal_saves")
parse(soup.find("table", {"id": "tableShamanHard"}), "hard_saves")
parse(soup.find("table", {"id": "tableShamanDivine"}), "divine_saves")
parse(soup.find("table", {"id": "tableShamanNormal"})[1], "without_skill_saves")

cheese_totals = list(mousebot_titles.find({"type": "cheese_total"}, { "_id": 0, "type": 0}))
cheese_firsts = list(mousebot_titles.find({"type": "cheese_first"}, { "_id": 0, "type": 0}))
bootcamps = list(mousebot_titles.find({"type": "bootcamp"}, { "_id": 0, "type": 0}))
# shops = list(mousebot_titles.find({"type": "shop"}, { "_id": 0, "type": 0}))

normal_saves = list(mousebot_titles.find({"type": "normal_saves"}, { "_id": 0, "type": 0}))
hard_saves = list(mousebot_titles.find({"type": "hard_saves"}, { "_id": 0, "type": 0}))
divine_saves = list(mousebot_titles.find({"type": "divine_saves"}, { "_id": 0, "type": 0}))
without_skill_saves = list(mousebot_titles.find({"type": "without_skill_saves"}, { "_id": 0, "type": 0}))

# print(cheese_totals)
# print(cheese_firsts)
# print(bootcamps)
# print(shops)

# print(normal_saves)
# print(hard_saves)
# print(divine_saves)
# print(without_skill_saves)


# Scrape Map Categories

url = "https://transformice.fandom.com/wiki/Map#Map_categories"
html = get(url)
soup = Soup(html)

table = soup.find("table", {"class": "wikitable centertext"})

for item in table.find("tr")[1:]:
    id = item.find("td")[0].text
    name = item.find("td")[2].text
    description = str(item.find("td")[3])

    if len(name) > 0:
        enums.insert_one({"type": "map_category", "data": {"id": id, "name": name, "description": description}})



# Scrape item pages enum

url = "https://transformice.fandom.com/wiki/Shop"
html = get(url)
soup = Soup(html)

table = soup.find("table", {"class": "wikitable"})[0]

row = table.find("tr")[1].find("td")


for category in row:
    cat = category.find('a').attrs.get('href')
    category_url = f"https://transformice.fandom.com{cat}"
    category_page = Soup(get(category_url))
    category_id = str(category_page.find("p")[0]).split(" ")[-1].split(".")[0]
    is_shaman = False
    if cat == "/wiki/Shop/Colors":
        category_id = 226
    elif cat == "/wiki/Shop/Shaman":
        category_id = "Shaman"
        is_shaman = True
    else:
        category_id = int(category_id)

    category_tables = category_page.find("table", {"class": "wikitable"})[1:]

    if not is_shaman:
        category_tables = [category_tables[0]]
    
    for i, cat_table in enumerate(category_tables):
        if is_shaman:
            category_id = i+1
        for item in cat_table.find("tr")[1:]:
            item_id = item.find("td")[0].text
            img = item.find("td")[1].find("img").attrs.get("data-src")

            shop_items.insert_one({"category": category_id, "item_id": int(item_id), "is_shaman": is_shaman, "img": img})
