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
    last_index = measures.index.tolist()[-1]
    # Line below causes copy warning but don't know why
    epochs = measures[(measures['Transitions'] != 0) | (measures.index == last_index)]

    epochs['EpochLength'] = epochs['DayNumber'].diff()
    epochs['EpochWeightGain'] = epochs['SmoothedWeight'].diff()
    epochs['EpochLength'] = epochs['EpochLength'].shift(-1)
    epochs['EpochWeightGain'] = epochs['EpochWeightGain'].shift(-1)
    epochs.insert(0, 'EpochNumber', range(0, len(epochs)))

    epochs = epochs[:-1]
    return epochs


def MakeMsg(measure_df, epochs):
    weight_today = measure_df.ix[-1, "WeightItp"]
    weight_gain_rate = (measure_df.ix[-1, "WeightItp"] - measure_df.ix[-15, "WeightItp"]) / 2
    last_weighed_record = measure_df[measure_df["DaysSinceLastWeigh"] == 0]
    days_since_last_weigh = measure_df.tail(1)["DaysSinceLastWeigh"].tolist()[0]

    subject = str("You weigh %.2f kg you fat pie" % weight_today)
    if weight_gain_rate > 0:
        body = str("You are currently gaining weight at %.2f kg per week" % weight_gain_rate)
    else:
        body = str("You are currently losing weight at %.2f kg per week" % -weight_gain_rate)
    if days_since_last_weigh > 0:
        body += str(
            "\nYou last weighed yourself %d days ago when you weighed %.2f. \n"
            "At a weight gain of %.3f kg per day that means you probably now weigh %.2f kg" \
            % (days_since_last_weigh,
               last_weighed_record["Weight"].tolist()[0],
               daily_weight_gain,
               weight_today)
        )
    body += '\n\nWeight today: {:.2f}kg\nA week ago: {:.2f}kg\nA month ago: {:.2f}kg\nA year ago: {:.2f}kg\n5 years ago: {:.2f}kg '.format(
        measure_df.iloc[-1]['WeightItp'],
        measure_df.iloc[-8]['WeightItp'],
        measure_df.iloc[-32]['WeightItp'],
        measure_df.iloc[-366]['WeightItp'],
        measure_df.iloc[-1 - 365 * 5]['WeightItp'],
    )

    body += "\n\nYou are in the {:d}th epoch, which has lasted {} days and began on {}".format(
        epochs.iloc[-1]['EpochNumber'], int(epochs.iloc[-1]['EpochLength']), epochs.iloc[-1].name.strftime('%Y-%m-%d')
    )
    body += "\nSo far this epoch you have {} {:.2f}kg, or {:.2f}kg per week".format(
        'gained' if epochs.iloc[-1]['EpochWeightGain'] >= 0 else 'lost',
        abs(epochs.iloc[-1]['EpochWeightGain']),
        abs(epochs.iloc[-1]['EpochWeightGain']) / epochs.iloc[-1]['EpochLength'] * 7

    )

    body += "\n\nThe previous epoch lasted {} days and began on {}".format(
        int(epochs.iloc[-2]['EpochLength']), epochs.iloc[-2].name.strftime('%Y-%m-%d')
    )
    body += "\nIn that epoch you {} {:.2f}kg, or {:.2f}kg per week".format(
        'gained' if epochs.iloc[-2]['EpochWeightGain'] >= 0 else 'lost',
        abs(epochs.iloc[-2]['EpochWeightGain']),
        abs(epochs.iloc[-2]['EpochWeightGain']) / epochs.iloc[-2]['EpochLength'] * 7

    )

    message = 'Subject: {}\n\n{}'.format(subject, body)
    return message


def PieMail():
    measures = GetMeasures()
    processed = ProcessMeasures(measures)
    epochs = CreateEpochs(processed)
    msg = MakeMsg(processed, epochs)
    SendMail(msg)
    return


if __name__ == "__main__":
    schedule.every().day.at("9:00").do(PieMail)

    while True:
        schedule.run_pending()
        time.sleep(1)


# Generally true to say that if you haven't weighed yourself for 5 or more days are gaining weight at a rate of 25g per day




