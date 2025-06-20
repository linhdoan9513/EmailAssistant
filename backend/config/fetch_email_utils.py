from langchain_core.documents import Document
import imaplib, email
from email.header import decode_header
from dotenv import load_dotenv
import os

def fetch_emails():
    load_dotenv()
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_address, email_password)
    mail.select("inbox")
    status, messages = mail.search(None, "ALL")

    docs = []
    for num in messages[0].split()[:100]:
        _, msg_data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        subject, _ = decode_header(msg["Subject"])[0]
        sender = msg.get("From")
        date = msg.get("Date")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        docs.append(Document(page_content=body, metadata={"subject": subject, "from": sender, "date": date}))
    return docs