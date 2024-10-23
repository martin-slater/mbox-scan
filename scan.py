# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import argparse
import os
import mailbox
import shutil
import json
import bs4
import re

from datetime import datetime

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def makedir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def clean_string(bytes):
    # delete all instances of u200b/u+200b
    return bytes.replace('\u200b', '')


def get_html_text(html):
    try:
        return bs4.BeautifulSoup(html, 'lxml').body.get_text(' ', strip=True)
    except AttributeError:  # message contents empty
        return None


def clean_filename(filename):
    if filename is None:
        return "unnamed"
    return re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "-", filename)


# -----------------------------------------------------------------------------
# Class
# -----------------------------------------------------------------------------

class Scan(object):
    """  """
    MailFile = "mailbox.mbox"

    def __init__(self, args):
        """ Constructor """
        self.temp_dir = ".output"

        with open(args.configFile) as f:
            self.config = json.load(f)
            self.temp_dir = os.path.join(
                ".output", os.path.splitext(os.path.basename(args.configFile))[0])

        self.temp_raw = os.path.join(self.temp_dir, "raw")
        self.temp_text = os.path.join(self.temp_dir, "text")

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        makedir(self.temp_dir)
        makedir(self.temp_raw)
        makedir(self.temp_text)

    def read_email_payload(self, email_data):
        email_payload = email_data.get_payload()
        if email_data.is_multipart():
            email_messages = list(self._get_email_messages(email_payload))
        else:
            email_messages = [email_payload]
        return [self._read_email_text(msg) for msg in email_messages]

    def read_email_attachments(self, filename, email_data):
        email_payload = email_data.get_payload()
        if email_data.is_multipart():
            email_messages = list(self._get_email_messages(email_payload))
        else:
            email_messages = [email_payload]
        return [self._read_attachments(filename, msg) for msg in email_messages]

    def _read_attachments(self, filename, msg):
        content_type = 'NA' if isinstance(msg, str) else msg.get_content_type()
        encoding = 'NA' if isinstance(msg, str) else msg.get(
            'Content-Transfer-Encoding', 'NA')

        if content_type in ["application/msword", "application/pdf"]:
            name = msg.get_param('name')
            fname = f"{filename}-{clean_filename(name)}"
            f = open(fname, "w+b")
            f.write(msg.get_payload(None, True))
            f.close()
            return fname

    def _get_email_messages(self, email_payload):
        for msg in email_payload:
            if isinstance(msg, (list, tuple)):
                for submsg in self._get_email_messages(msg):
                    yield submsg
            elif msg.is_multipart():
                for submsg in self._get_email_messages(msg.get_payload()):
                    yield submsg
            else:
                yield msg

    def _read_email_text(self, msg):
        content_type = 'NA' if isinstance(msg, str) else msg.get_content_type()
        encoding = 'NA' if isinstance(msg, str) else msg.get(
            'Content-Transfer-Encoding', 'NA')

        if 'text/plain' in content_type:  # and 'base64' not in encoding:
            msg_text = msg.get_payload(decode=True).decode("utf-8", "ignore")
        elif 'text/html' in content_type:  # and 'base64' not in encoding:
            msg_text = get_html_text(msg.get_payload(
                decode=True).decode("utf-8", "ignore"))
        elif content_type == 'NA':
            msg_text = get_html_text(msg)
        else:
            msg_text = None
        return (content_type, encoding, msg_text)

    def run(self):
        msg_epoch = datetime(2024, 3, 1).timestamp()

        def search(searchTerms, text):
            if text is None:
                return False

            text = text.lower()
            for s in searchTerms:
                regex = re.compile(r"\b" + s + r"\b", re.IGNORECASE)
                if len(regex.findall(text)) > 0:
                    return True
            return False

        msgs = mailbox.mbox(Scan.MailFile)
        index = 0
        for msg in msgs:
            date_prop = msg['Date']
            date_str = date_prop
            date = None

            start = date_prop.find(",") + 1
            if start == -1:
                start = 0

            end = date_prop.find("(")
            if end == -1:
                end = None

            date_str = date_prop[start:end].strip()
            date_str = date_str.replace("GMT", "+0000")
 #
            date = datetime.strptime(date_str, "%d %b %Y %H:%M:%S %z")

            subject = msg['subject']
            to = msg['To']
            cc = msg['Cc']
            sender = msg['From']  # .get_from()

            payload = self.read_email_payload(msg)
            contents = ""
            for p in payload:
                if p[2]:
                    contents += p[2] + "\n"

            if date.timestamp() > msg_epoch and (
                    search(self.config["generalSearchTerms"], contents) or
                    search(self.config["subjectSearchTerms"], subject) or
                    search(self.config["fromSearchTerms"], sender) or
                    search(self.config["toSearchTerms"], to) or
                    search(self.config["toSearchTerms"], cc)):
                # output raw email
                filename_root = f"{date.year:04d}-{date.month:02d}-{date.day:02d}-{
                    date.hour:02d}-{date.minute:02d}-{date.second:02d}"
                filename = f"{filename_root}.txt"
                f = open(os.path.join(self.temp_raw, filename),
                         "w+t")
                f.write(msg.__str__())
                f.close()

                # output text email
                f = open(os.path.join(self.temp_text, filename),
                         "w+t", encoding='utf-8')
                f.write(f"DATE    : {date_str}\n")
                f.write(f"SUBJECT : {subject}\n")
                f.write(f"FROM    : {sender}\n")
                f.write(f"TO      : {to}\n")
                f.write(f"CC      : {cc}\n")
                f.write("\n")
                f.write(contents)
                f.close()

                # output attachments
                self.read_email_attachments(os.path.join(
                    self.temp_text, filename_root), msg)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main():
    """ Main script entry point """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configFile", type=str)
    args = parser.parse_args()
    return Scan(args).run()


if __name__ == "__main__":
    main()
