from mywithings import WithingsApi
import pickle
import smtplib
import datetime
from settings import gmail_username, gmail_password
import pandas as pd
import numpy as np
import schedule
import time

daily_weight_gain = 0.025  # In general gain about 25g per day once "off the wagon"


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
    toaddrs = 'jweob1711@gmail.com'
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()


def ProcessMeasures(measure_df):
    measure_df["Date"] = pd.to_datetime(measure_df["DateTime"].dt.date)

    measure_df = measure_df.drop_duplicates(subset=["Date"])

    idx = pd.date_range(measure_df["Date"].min(), datetime.date.today())
    measure_df = measure_df.set_index(["Date"])

    measure_df = measure_df.reindex(idx)
    measure_df.insert(0, 'DayNumber', range(0, len(measure_df)))
    last_weighed_record = measure_df[measure_df['DateTime'].notnull()].tail(1)

    measure_df.insert(0, 'DaysSinceLastWeigh', measure_df['DayNumber'] - last_weighed_record['DayNumber'].tolist()[0])
    measure_df["WeightItp"] = measure_df.interpolate()["Weight"]
    measure_df.loc[(measure_df["DaysSinceLastWeigh"] > 0), 'WeightItp'] = \
        measure_df[measure_df["DaysSinceLastWeigh"] > 0]['WeightItp'] + \
        measure_df[measure_df["DaysSinceLastWeigh"] > 0]['DaysSinceLastWeigh'] * daily_weight_gain
    measure_df["FatItp"] = measure_df.interpolate()["Fat"]
    measure_df.loc[(measure_df["DaysSinceLastWeigh"] > 0), 'FatItp'] = \
        measure_df[measure_df["DaysSinceLastWeigh"] > 0]['FatItp'] + \
        measure_df[measure_df["DaysSinceLastWeigh"] > 0]['DaysSinceLastWeigh'] * daily_weight_gain

    # Fields for Epochs
    measure_df['SmoothedWeight'] = measure_df['WeightItp'].rolling(window=7).mean()
    measure_df['SmoothedWeightGain'] = measure_df['SmoothedWeight'].diff(periods=7)
    measure_df['GainOrLoss'] = measure_df['SmoothedWeightGain'].map(lambda x: 1 if x >= 0 else -1)
    measure_df['Transitions'] = measure_df['GainOrLoss'].diff(periods=1)
    first_index = measure_df.index.tolist()[0]
    last_index = measure_df.index.tolist()[-1]

    if measure_df.iloc[1]['GainOrLoss'] == -1:
        measure_df.loc[first_index, 'Transitions'] = -2
    else:
        measure_df.iloc[first_index, 'Transitions'] = 2

    return measure_df


def CreateEpochs(measures):
    # Line below causes copy warning but don't know why
    epochs = measures[(measures['Transitions'] != 0) | (measures.index == last_index)]

    epochs['EpochLength'] = epochs['DayNumber'].diff()
    epochs['EpochWeightGain'] = epochs['SmoothedWeight'].diff()
    epochs['EpochLength'] = epochs['EpochLength'].shift(-1)
    epochs['EpochWeightGain'] = epochs['EpochWeightGain'].shift(-1)
    epochs.insert(0, 'EpochNumber', range(0, len(epochs)))

    epochs = epochs[:-1]
    return epochs


def AnalyseMeasures(measure_df):
    results = {}
    results["WeightToday"] = measure_df.ix[-1, "WeightItp"]
    results["WeightGainRate"] = (measure_df.ix[-1, "WeightItp"] - measure_df.ix[-15, "WeightItp"]) / 2
    results["LastWeighedRecord"] = measure_df[measure_df["DaysSinceLastWeigh"] == 0]
    results["DaysSinceLastWeigh"] = measure_df.tail(1)["DaysSinceLastWeigh"].tolist()[0]
    return results


def MakeMsg(results, epochs):
    subject = str("You weigh %.2f kg you fat pie" % results["WeightToday"])
    if results["WeightGainRate"] > 0:
        body = str("You are currently gaining weight at %.2f kg per week" % results["WeightGainRate"])
    else:
        body = str("You are currently losing weight at %.2f kg per week" % -results["WeightGainRate"])
    if results["DaysSinceLastWeigh"] > 0:
        body += str(
            "\nYou last weighed yourself %d days ago when you weighed %.2f. \n"
            "At a weight gain of %.3f kg per day that means you probably now weigh %.2f kg" \
            % (results["DaysSinceLastWeigh"],
               results["LastWeighedRecord"]["Weight"].tolist()[0],
               daily_weight_gain,
               results["WeightToday"])
        )

    body += str("\nYou are in the %dth epoch, which has lasted %d days" \
                "\nSo far you have gained %.2fkg"

                % (epochs.iloc[-1]['EpochNumber'], epochs.iloc[-1]['EpochLength'], epochs.iloc[-1]['EpochWeightGain'])
                )

    message = 'Subject: {}\n\n{}'.format(subject, body)
    return message


def PieMail():
    measures = GetMeasures()
    processed = ProcessMeasures(measures)
    results = AnalyseMeasures(processed)
    epochs = CreateEpochs(measures)
    msg = MakeMsg(results, epochs)
    SendMail(msg)
    return


if __name__ == "__main__":

    schedule.every().day.at("9:00").do(PieMail)

    while True:
        schedule.run_pending()
        time.sleep(1)


# Generally true to say that if you haven't weighed yourself for 5 or more days are gaining weight at a rate of 25g per day




