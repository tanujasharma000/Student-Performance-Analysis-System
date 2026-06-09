import smtplib
from email.message import EmailMessage

def send_email(receiver,name,marks):

    sender=""
    password=""

    msg=EmailMessage()

    msg['Subject']="Student Performance Alert"
    msg['From']=sender
    msg['To']=receiver

    msg.set_content(f"""
Hello {name},

Your average marks are {marks:.2f}

Your performance is below the required level.
Please focus on improving your studies.

Regards
Student Performance Analysis System
""")

    try:
        with smtplib.SMTP('smtp.gmail.com',587) as server:
            server.starttls()
            server.login(sender,password)
            server.send_message(msg)
    except Exception as e:
        print("Email error:",e)
