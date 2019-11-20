import csv


finalData = []
with open('../data/custom_data.csv', newline='') as csvfile:
	for row in csv.reader((line.replace('\0','') for line in csvfile), delimiter=","):
	# for row in reader:
		flag = True
		for user in finalData:
			if(user["name"] == row[2]):
				user["records"].append(row[0])
				flag = False
				break;
		if(flag):
			print("new user : " + row[2])
			user = {}
			user["name"] = row[2]
			user["records"] = [row[0]]
			finalData.append(user)


with open("train_balanced_user_custom.csv", 'w') as output_file:
        writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
        writer.writerows((user["name"], " <END> ".join(user["records"]))
                         for user in finalData)
