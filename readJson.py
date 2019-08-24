import json

res = None

with open("json.txt") as file:
	res = json.load(file)

if res:
	
	tpSet = set()

	for element in res:
		tp = element["type"]
		tpSet.add(tp)
		
	print tpSet


