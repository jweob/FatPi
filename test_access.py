from mywithings import WithingsApi
import pickle

with open('creds.pkl', 'rb') as input:
    creds = pickle.load(input)

client = WithingsApi(creds)
measures = client.get_measures()
measurelist = []
for measure in measures:
    measurelist.append([measure.date, measure.weight])

print(measurelist)

# Generally true to say that if you haven't weighed yourself for 5 or more days are gaining weight at a rate of 25g per day




