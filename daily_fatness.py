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
        measurelist.append({"date": measure.date, "weight": measure.weight, "fat": measure.fat_mass_weight})
    return measurelist

def GetMeasures2():
    with open('creds.pkl', 'rb') as input:
        creds = pickle.load(input)

    client = WithingsApi(creds)
    measures = client.get_measures()
    measurelist = []
    for measure in measures:
        measurelist.append([measure.date, measure.weight, measure.fat_mass_weight])
    measure_df = pd.DataFrame(measurelist, columns=["DateTime", "Weight", "Fat"])
    return measure_df

def ProcessMeasures(measure_df):
    measure_df["Date"] = pd.to_datetime(measure_df["DateTime"].dt.date)

    measure_df = measure_df.drop_duplicates(subset=["Date"])

    idx = pd.date_range(measure_df["Date"].min(), measure_df["Date"].max())
    measure_df = measure_df.set_index(["Date"])

    measure_df = measure_df.reindex(idx)
    measure_df = measure_df.interpolate()
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

def MakeMsg(subject, body):
    message = 'Subject: {}\n\n{}'.format(subject, body)
    return message

def SortMeasures(measures):
    measure_dict = {}
    sorted_records = []
    today_date = datetime.date.today()
    min_date = datetime.date.today()
    for measure in measures:
        measure_date = datetime.date(measure["date"].year, measure["date"].month, measure["date"].day)
        if measure_date not in measure_dict:
            measure_dict[measure_date] = measure
        if measure_date < min_date:
            min_date = measure_date

    days = (today_date - min_date).days + 1

    for day_index in range(days):
        day = today_date - datetime.timedelta(day_index)
        if day in measure_dict:
            sorted_records.append(measure_dict[day])
            sorted_records[-1]["date"] = day
            sorted_records[-1]["interpolated"] = False

    interpolated_records = []

    for day_index in range(days):
        day = today_date - datetime.timedelta(day_index)


    return sorted_records



def PieMail():
    measures = GetMeasures()
    body = ""
    last_measure = measures[0]
    print(last_measure)
    body += "You last weighed yourself "


    subject = "Your weight is " + str(measures[0]["weight"]) + " kg"
    body = "You fat pie"
    print(body)
    # SendMail(MakeMsg(subject, body))


if __name__ == "__main__":
    measures = GetMeasures2()
    measures = ProcessMeasures(measures)
    print(measures.tail(50))
    """
    schedule.every().day.at("20:50").do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
    """

# Generally true to say that if you haven't weighed yourself for 5 or more days are gaining weight at a rate of 25g per day




