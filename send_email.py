# Import smtplib for the actual sending function
import smtplib
from settings import gmail_username, gmail_password


server = smtplib.SMTP('smtp.gmail.com:587')
server.ehlo()
server.starttls()
server.login(gmail_username, gmail_password)

fromaddr = 'jweob1711@gmail.com'
toaddrs  = 'jweob1711@gmail.com'
msg = 'Why,Oh why!'



server.sendmail(fromaddr, toaddrs, msg)
server.quit()