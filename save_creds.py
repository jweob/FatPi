from mywithings import WithingsAuth, WithingsApi
from settings import CONSUMER_KEY, CONSUMER_SECRET, oauth_token, oauth_verifier
import pickle

# Saves credentials to a pickle object for later use

def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)


auth = WithingsAuth(CONSUMER_KEY, CONSUMER_SECRET)
authorize_url = auth.get_authorize_url()
print("Go to %s allow the app and copy your oauth_verifier" % authorize_url)

oauth_verifier = input('Please enter your oauth_verifier: ')
creds = auth.get_credentials(oauth_verifier)

"""
# sample usage
save_object(creds, 'creds.pkl')

client = WithingsApi(creds)
measures = client.get_measures(limit=1)
print("Your last measured weight: %skg" % measures[0].weight)
"""


