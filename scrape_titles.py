from gazpacho import get, Soup
import pymongo

mongo_client = pymongo.MongoClient()
mousebot_db = mongo_client['mousebot']
mousebot_titles = mousebot_db['titles']

# Empty Titles database
mousebot_titles.delete_many({})

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
