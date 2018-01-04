from mywithings import WithingsApi
import pickle
import smtplib
import datetime
from settings import gmail_username, gmail_password
import pandas as pd
import numpy as np
import schedule
import time

def GetMeasures():
    with open('creds.pkl', 'rb') as input:
        creds = pickle.load(input)

    client = WithingsApi(creds)
    measures = client.get_measures()
    measurelist = []
    for measure in measures:
        measurelist.append([measure.date, measure.weight, measure.fat_mass_weight])
    measure_df = pd.DataFrame(measurelist, columns=["DateTime", "Weight", "Fat"])
    return measure_df

def SendMail(msg):
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(gmail_username, gmail_password)

    fromaddr = 'jweob1711@gmail.com'
    toaddrs  = 'jweob1711@gmail.com'
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

def ProcessMeasures(measure_df):
    measure_df["Date"] = pd.to_datetime(measure_df["DateTime"].dt.date)

    measure_df = measure_df.drop_duplicates(subset=["Date"])

    idx = pd.date_range(measure_df["Date"].min(), datetime.date.today())
    measure_df = measure_df.set_index(["Date"])

    measure_df = measure_df.reindex(idx)
    measure_df["WeightItp"] = measure_df.interpolate()["Weight"]
    measure_df["FatItp"] = measure_df.interpolate()["Fat"]
    return measure_df

def AnalyseMeasures(measure_df):
    results = {}
    results["WeightToday"] = measure_df.ix[-1, "Weight"]
    results["WeightGainRate"] = (measure_df.ix[-1, "WeightItp"] - measure_df.ix[-15, "WeightItp"]) / 2
    return results

def MakeMsg(results):
    subject = str("You weigh %.2f kg you fat pie" % results["WeightToday"])
    if results["WeightGainRate"] > 0:
        body = str("You are currently gaining weight at %.2f kg per week" % results["WeightGainRate"])
    else:
        body = str("You are currently losing weight at %.2f kg per week" % -results["WeightGainRate"])
    message = 'Subject: {}\n\n{}'.format(subject, body)
    return message


def PieMail():
    measures = GetMeasures()
    processed = ProcessMeasures(measures)
    results = AnalyseMeasures(processed)
    msg = MakeMsg(results)
    SendMail(msg)
    return


if __name__ == "__main__":


    schedule.every().day.at("9:00").do(PieMail)

    while True:
        schedule.run_pending()
        time.sleep(1)


# Generally true to say that if you haven't weighed yourself for 5 or more days are gaining weight at a rate of 25g per day




