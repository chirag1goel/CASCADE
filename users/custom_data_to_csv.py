import csv


finalData = []
with open('../data/custom_data.csv', newline='') as csvfile:
	reader = csv.reader(csvfile, delimiter=',')
	for row in reader:
		flag = True
		for user in finalData:
			if(user["name"] == row[1]):
				user["records"].append(row[0])
				flag = False
				break;
		if(flag):
			user = {}
			user["name"] = row[1]
			user["records"] = [row[0]]
			finalData.append(user)


with open("train_balanced_user_custom.csv", 'w') as output_file:
        writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
        writer.writerows((user["name"], " <END> ".join(user["records"]))
                         for user in iteritems(finalData))
