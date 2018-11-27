from __future__ import print_function
from apiclient.discovery import build
from apiclient import errors

from httplib2 import Http
from oauth2client import file, client, tools
import urllib


import logging
logging.basicConfig()


from flask import *
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from apiclient.http import MediaIoBaseDownload
from werkzeug import secure_filename
from flask_cors import CORS
import io
import time, datetime
import shutil
import re
import os
import requests, calendar
from apscheduler.scheduler import Scheduler
from pytz import timezone
import pytz
from io import BytesIO

path = os.path.dirname(__file__)
# modify this to change the Template Directory

app = Flask(__name__)
CORS(app)
""""Schedular"""
sched = Scheduler()  # Scheduler object
sched.start()


# final 6/30/18

def getfilenamebyId(service, file_id):
    try:
        file = service.files().get(fileId=file_id).execute()
        if file['mimeType'] == 'application/vnd.google-apps.folder':
            return ""
        else:
            return file['title']
    except:
        pass
        return ""


# final 6/30/18

def download(service, fileIds, prefix):
    fileNames = []
    for id in fileIds:
        result = getfilenamebyId(service, id)
        if result != "":
            name = prefix + "/" + result
            fileNames.append(name)
            req = service.files().get_media(fileId=id)
            fh = io.FileIO(name, 'w')
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            try:
                while done is False:
                    status, done = downloader.next_chunk()
            except Exception as inst:
                return "Failed in downloading html file. please check fileId again"
            fh.close()
    return fileNames


# final 6/30/18

class EmailTemplate():
    def __init__(self, template_name='', values={}, html=True):
        self.template_name = template_name
        self.values = values
        self.html = html

    def render(self):
        content = open(self.template_name).read()

        for k, v in self.values.items():
            content = content.replace('[%s]' % k, v)
        return content


# final 6/30/18

class MailMessage(object):
    html = False

    def __init__(self, from_email='', to_emails=[], cc_emails=[], reply_to=[], subject='', body='', qattachment='',
                 template=None, templatefiles=[], attachments=[]):
        self.from_email = from_email
        self.reply_to = reply_to
        self.to_emails = to_emails
        self.cc_emails = cc_emails
        self.subject = subject
        self.template = template
        self.body = body
        self.file_attachments = attachments
        self.templatefiles = templatefiles
        self.qattachment = qattachment

    def attach_file(self, path):
        self.file_attachments.append(path)

    def get_message(self):
        if isinstance(self.to_emails, str):
            self.to_emails = [self.to_emails]

        if isinstance(self.reply_to, str):
            self.reply_to = [self.reply_to]

        if isinstance(self.cc_emails, str):
            self.cc_emails = [self.cc_emails]

        if isinstance(self.qattachment, str):
            self.qattachment = [self.qattachment]

        if len(self.to_emails) == 0 or self.from_email == '':
            raise ValueError('Invalid From or To email address(es)')

        msg = MIMEMultipart('alternative')
        # msg = MIMEMultipart('multipart/mixed')
        msg['To'] = ', '.join(self.to_emails)
        msg['Reply-to'] = ', '.join(self.reply_to)
        msg['Cc'] = ', '.join(self.cc_emails)
        msg['From'] = self.from_email
        msg['Subject'] = self.subject

        msgAlternative = MIMEMultipart('mixed')
        msg.attach(msgAlternative)

        msgText = MIMEText('This is the alternative plain text message.')
        msgAlternative.attach(msgText)

        if self.template:
            if self.template.html:
                msgAlternative.attach(MIMEText(self.template.render(), 'html'))
            else:
                msgAlternative.attach(MIMEText(self.template.render(), 'plain'))
        else:
            msgAlternative.attach(MIMEText(self.body, 'plain'))

        for file in self.templatefiles:
            # ORIG with open(attachment, "rb") as f:
            # ORIGfilename = os.path.basename(attachment)
            fp = open(file, 'rb')
            msgImage = MIMEImage(fp.read())
            fp.close()
            cids = file.split("/")
            cid = cids[len(cids) - 1]
            msgImage.add_header('Content-ID', '<' + cid + '>')
            msgImage.add_header('Content-Disposition', 'inline', filename=os.path.basename(file))
            msg.attach(msgImage)

        for attachment in self.file_attachments:
            with open(attachment, "rb") as f:
                filename = os.path.basename(attachment)
                part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = 'attachment; filename="' + str(filename) + '"'
                msg.attach(part)
        try:
            if self.qattachment != "" and os.path.exists(self.qattachment):
                with open(self.qattachment, "rb") as f:
                    filename = os.path.basename(self.qattachment)
                    part = MIMEApplication(f.read(), Name=filename)
                    part['Content-Disposition'] = 'attachment; filename="' + str(filename) + '"'
                    msg.attach(part)
        except:
            pass
        # ORIG part = MIMEApplication(f.read(), Name=filename)
        # ORIG part['Content-Disposition'] = 'attachment; filename="' + str(filename) + '"'
        # ORIG msg.attach(part)
        return msg


# final 6/30/18

class MailServer(object):
    msg = None

    def __init__(self, server_name='smtp.gmail.com', username='<username>', password='<password>', port=587,
                 require_starttls=True):
        self.server_name = server_name
        self.username = username
        self.password = password
        self.port = port
        self.require_starttls = require_starttls


# final 6/30/18

def send(mail_msg, mail_server=MailServer()):
    server = smtplib.SMTP(mail_server.server_name, mail_server.port)
    if mail_server.require_starttls:
        server.starttls()
    if mail_server.username:
        server.login(mail_server.username, mail_server.password)

    server.sendmail(mail_msg.from_email, (mail_msg.to_emails + mail_msg.cc_emails), mail_msg.get_message().as_string())
    server.close()


# final 6/30/18

def getConnection():
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage(path + '/credentials.json')
    creds = store.get()

    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(path + '/client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)

    service = build('drive', 'v2', http=creds.authorize(Http()))
    return service


# final 6/30/18

def get_files_in_folder(service, folder_id):
    """Print files belonging to a folder.

    Args:
      service: Drive API service instance.
      folder_id: ID of the folder to print files from.
    """
    page_token = None
    file_ids = []
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            children = service.children().list(
                folderId=folder_id, **param).execute()

            for child in children.get('items', []):
                file_ids.append(child['id'])
            page_token = children.get('nextPageToken')
            if not page_token:
                break
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            break

    return file_ids


# final 6/30/18
def get_fileNames_in_folder(service, folder_id):
    """Print files belonging to a folder.

    Args:
      service: Drive API service instance.
      folder_id: ID of the folder to print files from.
    """
    page_token = None
    file_ids = []
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            # children = service.children().list(
            #        folderId=folder_id, **param).execute()
            query = "'{}' in parents".format(folder_id)
            children = service.files().list(
                q=query, fields='nextPageToken, files(id, name)').execute()
            return children
            for child in children.get('items', []):
                return child
                file_ids.append(child['name'])
            page_token = children.get('nextPageToken')
            if not page_token:
                break
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            break
    return file_ids


# final 6/30/18
@app.route('/')
def hello_world():
    return render_template('index.html')


# NOTfinal 6/30/18

@app.route('/sendEmail', methods=['POST'])
def sendEmail():
    if request.method == 'POST':
        ##############  Get params from request ###############
        ##   reply_to   :  destination email
        ##   file_id    :  email file id of google drive  %% You can get file id using this end point "ec2-18-216-179-182.us-east-2.compute.amazonaws.com/fileList"
        ##   subject    :  Subject of Email
        ##   attachment :  attach file params
        ##   address    :  Address information
        ##   price      :  Price param
        ##   name       :  Name param
        #######################################################

        if 'msg[Reply_to]' in request.form:
            Reply_to = request.form['msg[Reply_to]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[Reply_to]'"})

        if 'msg[To]' in request.form:
            Email_To = request.form['msg[To]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[To]'"})

        templateID_folder = ""
        if 'templateID_folder' in request.form:
            templateID_folder = request.form['templateID_folder']

        if 'attachFiles' not in request.form:
            return json.dumps({"error": "Failed! Missing parameter 'templateID_folder' or 'attachFiles'"})

        if 'address' in request.form:
            address = request.form['address']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'address'"})

        if 'price' in request.form:
            price = request.form['price']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'price'"})

        if 'name' in request.form:
            name = request.form['name']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'name'"})

        templateID = ""
        if 'templateID' in request.form:
            templateID = request.form['templateID']
        elif 'template' not in request.files:
            return json.dumps({"error": "No template or templateID found!"})

        if 'subject' in request.form:
            subject = request.form['subject']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'subject'"})

        prefix = path + "/uploads/" + str(int(round(time.time() * 1000)))
        if not os.path.exists(prefix):
            os.makedirs(prefix)
            os.makedirs(prefix + "/attachments")

        if 'template' in request.files:
            uploadfile = request.files.getlist("template")
            for file in uploadfile:
                templateFileName = os.path.join(prefix + "/", secure_filename(file.filename))
                file.save(templateFileName)

        attachFileNames = []
        if 'attachFiles' in request.files:
            uploadsFiles = request.files.getlist("attachFiles")
            for file in uploadsFiles:
                fileName = os.path.join(prefix + "/", secure_filename(file.filename))
                attachFileNames.append(fileName)
                file.save(fileName)

        ## get instance of connection for google drive
        service = getConnection()

        if templateID != "":
            templateFileName = prefix + "/email.html"
            ## download file which id is file_id and save as "email.html"
            req = service.files().get_media(fileId=templateID)
            fh = io.FileIO(templateFileName, 'w')
            downloader = MediaIoBaseDownload(fh, req)

            done = False
            try:
                while done is False:
                    status, done = downloader.next_chunk()
            except Exception as inst:
                return json.dumps({"error": "Failed in downloading html file. please check fileId again"})
            fh.close()
        ### download attached files
        # templateID_folder = "1Tnw9ShNslKIwt7awqxQQ7Awva7rMXE3T"
        if templateID_folder != "":
            fileIds = get_files_in_folder(service, templateID_folder)
            attachFileNames = download(service, fileIds, prefix + "/attachments")

        ## Define values which are needed to exchange with email text.
        values = {}
        # values['username'] = 'mail@gmail.com'
        # values['from'] = 'mail@gmail.com'
        # values['url'] = ''
        femail = 'ashley@la-retrofit.com'
        femailp = 'TempPass123456@'
        # femail='matt.engineering79@gmail.com'
        if '@la-retrofit.com' in femail:
            servern = 'smtp.office365.com'
            port_ = 587
        if '@gmail.com' in femail:
            servern = 'smtp.gmail.com'
            port_ = 587

        ## Sending email to Email_To
        temp = EmailTemplate(template_name=templateFileName, values=values)
        server = MailServer(server_name=servern, username=femail,
                            password=femailp,
                            port=port_, require_starttls=True)
        msg = MailMessage(from_email=femail, to_emails=[Email_To], reply_to=[Reply_to], subject=subject, template=temp,
                          attachments=attachFileNames)
        send(mail_msg=msg, mail_server=server)

        ## delete downloaded files
        # os.remove(templateFileName)
        # for name in attachFileNames:
        #    if (os.path.exists(name)):
        #        os.remove(name)
        # shutil.rmtree(prefix)
        # return json.dumps({"success": "sent email to 2  " + Email_to})


# final 6/30/18
## Get file list of google drive
@app.route('/fileList')
def fileList():
    # Setup the Drive v2 API
    service = getConnection()
    print("here")
    result = []
    page_token = None
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            files = service.files().list(**param).execute()

            result.extend(files['items'])
            page_token = files.get('nextPageToken')
            if not page_token:
                break
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            break
    return json.dumps({'lists': result})

    #
    # # Call the Drive v2 API
    # results = service.files().list(
    #     fields="nextPageToken, files(id, name)").execute()
    # items = results.get('files', [])
    # if not items:
    #     return "File Not Found"
    # else:
    #     return json.dumps({'lists': items})


# final 6/30/18
# rest api to send email
@app.route('/restApi', methods=['POST'])
def uploads():
    if request.method == 'POST':
        # MAIN MAIN
        ##############  Get params from request ###############
        ##   reply_to   :  destination email
        ##   file_id    :  email file id of google drive  %% You can get file id using this end point "ec2-18-216-179-182.us-east-2.compute.amazonaws.com/fileList"
        ##   subject    :  Subject of Email
        ##   attachment :  attach file params
        ##   address    :  Address information
        ##   price      :  Price param
        ##   name       :  Name param
        #######################################################

        if 'msg[Reply_to]' in request.form:
            Reply_to = request.form['msg[Reply_to]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[Reply_to]'"})

        if 'msg[To]' in request.form:
            Email_To = request.form['msg[To]']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'msg[To]'"})

        Email_CC = ''
        if 'msg[CC]' in request.form:
            Email_CC = request.form['msg[CC]']

        templateID_folder = ""
        if 'templateID_folder' in request.form:
            templateID_folder = request.form['templateID_folder']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'templateID_folder'"})

        if 'attachFiles' in request.form:
            attachFiles = request.form['attachFiles'];
        else:
            return json.dumps({"error": "Failed! Missing parameter 'templateID_folder' or 'attachFiles'"})

        if 'address' in request.form:
            address = request.form['address']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'address'"})

        if 'price' in request.form:
            price = request.form['price']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'price'"})

        if 'name' in request.form:
            name = request.form['name']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'name'"})

        quote = 0
        if 'quote' in request.form:
            quote = int(request.form['quote'])
        else:
            quote = 0

        prclim = ""
        if 'prclim' in request.form:
            prclim = request.form['prclim']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'prclim'"})

        templateID = ""
        if 'templateID' in request.form:
            templateID = request.form['templateID']
        elif 'template' not in request.files:
            return json.dumps({"error": "No template or templateID found!"})

        if 'subject' in request.form:
            subject = request.form['subject']
        else:
            return json.dumps({"error": "Failed! Missing parameter 'subject'"})

        """finddeadline, deadline, fadr, remaining"""""""""
        finddeadline = 0
        if 'finddeadline' in request.form:
            finddeadline = request.form['finddeadline']

        """prefix"""
        prefix = path + "/uploads/" + str(int(round(time.time() * 1000)))
        if not os.path.exists(prefix):
            os.makedirs(prefix)

        directattach = 0
        if 'directattach' in request.form:
            directattach = request.form['directattach']
        else:
            directattach = ''

        ### download attached files
        service = getConnection()
        fileIds = attachFiles.replace(" ", "")
        fileIds = fileIds.split(",")
        attachFileNames = download(service, fileIds, prefix)
        if directattach != '':
            dattachs = directattach.split(",")
            for da in dattachs:
                tmp = da.rfind('/')
                fnm = da[tmp + 1:]
                if "http" not in da.lower():
                    da = da.replace('www.', 'http://www.')
                qr = requests.get(da, stream=True)
                qname = prefix + "/" + fnm
                fl = open(path + "/testfile2.txt", "a+")
                fl.write(da + "\n" + fnm + "\n" + qname + "\n")
                fl.close()
                with open(qname, "wb") as fl:
                    for chunk in qr.iter_content(chunk_size=128):
                        if chunk:
                            fl.write(chunk)
                            # REPLACES THE CONTENT OF EMAIL
                if os.path.isfile(qname):
                    attachFileNames.append(qname)

                    # attachFileNames = []
                    # if 'attachFiles' in request.files:
                    #     uploadsFiles = request.files.getlist("attachFiles")
                    #     for file in uploadsFiles:
                    #         fileName = os.path.join(prefix + "/", secure_filename(file.filename))
                    #         attachFileNames.append(fileName)
                    #         file.save(fileName)
                    #         fl = open(path+"/testfile2.txt","a+")
                    #  fl.write(fileName+"\n")
                    #  fl.close()

        textfile = open(path + "/queue.txt", 'a')
        content = {"Reply_to": Reply_to, "Email_To": Email_To, "templateID_folder": templateID_folder,
                   "templateID": templateID, "address": address, "price": price, "name": name, "subject": subject,
                   "finddeadline": finddeadline, "attachFileNames": attachFileNames,
                   "recieve_time": datetime.datetime.now().replace(microsecond=0).strftime('%m/%d/%Y-%H:%M:%S'),
                   "prclim": prclim, "quote": quote, "Email_CC": Email_CC}
        textfile.write(json.dumps(content) + '\n')
        textfile.close()
        return json.dumps({"success": "will send email to MAIN " + Email_To})
        # EmailSendingUint(Reply_to=Reply_to, Email_To=Email_To, templateID_folder=templateID_folder, templateID=templateID, address=address, price=price,name=name, subject=subject,finddeadline=finddeadline,attachFileNames=attachFileNames)


"""Email Send Unit for CronJob"""


def EmailSendingUint(prclim, Reply_to, Email_To, templateID_folder, templateID, address, price, name, subject,
                     finddeadline, quote, Email_CC, attachFileNames=[]):
    """finddeadline, deadline, fulladdress, remaining"""""""""
    remaining = 0
    fadr = ""
    clock = ""

    if finddeadline == '1' and address != "":
        url = "http://www.la-retrofit.com/getDEADLINE/index.php?address=" + address
        r = requests.get(url)
        data = str(r.content).split('<br>')
        deadline = ""
        fl = open(path + "/testfile.txt", "w")
        fl.write(finddeadline + "\n")
        fl.close()

        try:
            permit = data[0]
            deadline = data[1]
            fadr = data[2]

        except:
            pass
        if deadline != "":
            obj = datetime.datetime.strptime(deadline, "%m/%d/%Y")
            today = datetime.datetime.now().replace(hour=0).replace(minute=0).replace(second=0).replace(
                microsecond=0)
            obj = obj.replace(year=obj.year + 2)
            remaining = (obj - today).days
            clock = '<iframe src="http://free.timeanddate.com/countdown/i6b31n31/n137/cf13/cm0/cu1/ct0/cs0/ca0/co0/cr0/ss0/cac000/cpc000/pcf00/tcfff/fs100/szw320/szh135/iso' + str(
                obj.year) + '-' + str(obj.month) + '-' + str(
                obj.day) + 'T00:00:00/pa3" allowTransparency="true" frameborder="0" width="90" height="25"></iframe>'

    """date_"""""""""
    today = datetime.datetime.now(tz=pytz.utc)
    today = today.astimezone(timezone('US/Pacific'))
    day = today.day
    lastday = calendar.monthrange(today.year, today.month)[1]
    if day > int(lastday / 2):
        date_ = str(today.month) + "/" + str(lastday) + "/" + str(today.year)
    else:
        date_ = str(today.month) + "/" + str(int(lastday / 2)) + "/" + str(today.year)
    prclim = "$1500.0 Discount Already Applied - OFFER EXPIRES " + date_

    """prefix"""
    prefix = path + "/uploads/" + str(int(round(time.time() * 1000)))
    if not os.path.exists(prefix):
        os.makedirs(prefix)
        os.makedirs(prefix + "/attachments")

    ## get instance of connection for google drive
    service = getConnection()

    if templateID != "":
        templateFileName = prefix + "/email.html"
        ## download file which id is file_id and save as "email.html"
        req = service.files().get_media(fileId=templateID)
        fh = io.FileIO(templateFileName, 'w')
        downloader = MediaIoBaseDownload(fh, req)

        done = False
        try:
            while done is False:
                status, done = downloader.next_chunk()
        except Exception as inst:
            return json.dumps({"error": "Failed in downloading html file. please check fileId again"})
        fh.close()
    ## Define values which are needed to exchange with email text.
    values = {}

    ## Sending email to reply_to
    femail = 'honestdev21@gmail.com'
    femailp = 'ahgifrhehdejd'
    # femail = 'honestdev21@gmail.com'
    # femailp = 'ahgifrhehdejd'
    if '@la-retrofit.com' in femail:
        servern = 'smtp.office365.com'
        port_ = 587
    if '@gmail.com' in femail:
        servern = 'smtp.gmail.com'
        port_ = 587

    temp = EmailTemplate(template_name=templateFileName, values=values)
    temp_ = str(temp.render())
    # Fixing Unknown Characters

    # rep_ = r'windows-1252'
    # temp_ = unicode(temp_, "u")
    temp_ = re.sub(r'[^\x00-\x7F]+', ' ', temp_)
    # temp_=temp_.decode('utf-8')
    # GET FULL ADDRESS
    wds = address.split(" ")
    address = str.join('+', wds)
    url = 'https://maps.googleapis.com/maps/api/geocode/json?&key=AIzaSyAKUsjQYamRqDL8przA2r4msj_ppgCe80A&address=' + address + "+Los+ANGELES,CA,USA"
    resp = urllib.urlopen(url)
    jraw = resp.read()
    jdata = json.loads(jraw)
    if jdata['status'] == 'OK':
        result = jdata['results'][0]
        fadr = result['formatted_address']
        fadr_ = result['formatted_address']
    else:
        return "error"

    # download QUOTE
    qname = ""
    if quote == 1:
        qurl = "http://www.la-retrofit.com/action_page.php?password=laretrofit1&address=" + fadr + "&price=" + price + "&retainer1=60&retainer2=30&time=10&prclim=" + prclim;
        qr = requests.get(qurl, stream=True)
        qname = prefix + "/LA-Retrofit-Quote-" + fadr.replace(" ", "_").replace(".", "_").replace(",", "_") + ".pdf"
        qname = qname.replace("__", "_")
        with open(qname, "wb") as pdf:
            for chunk in qr.iter_content(chunk_size=1024):
                if chunk:
                    pdf.write(chunk)
                    # REPLACES THE CONTENT OF EMAIL
        if os.path.isfile(qname):
            qname = qname
        else:
            qname = ""

    temp_ = temp_.replace("Hi ,", "Hi " + name + ",")
    temp2 = "BUILDING 1 Address:<br>" + fadr
    temp_ = temp_.replace("BUILDING 1 Address:", temp2)

    # find the deadline
    bad = 0
    if finddeadline == '1' and clock != "":
        if ("west hollywood" not in fadr.lower()) and ("santa monica" not in fadr.lower()) and (
            "beverly hills" not in fadr.lower()):
            temp_ = temp_.replace('%DEADLINE%',
                                  '<span style="background-color:yellow">  ' + str(remaining) + '  </span>')
        else:
            bad = 1
    else:
        bad = 1
    if bad == 1:
        temp_ = temp_.replace('%DEADLINE%', '')
        temp_ = temp_.replace('DAYS LEFT TO CITY DEADLINE FOR YOUR PROPERTY', '')
        bad = 0

    if (prclim == ''):
        temp_ = temp_.replace("%PRICE%", '$' + price);
    else:
        temp_ = temp_.replace("%PRICE%", '$' + price + '  (' + prclim + ')');

    regex = r'<img[^>]+src=\"([^\">]+)'
    srcs = re.findall(regex, str(temp_))
    xn = 0
    imgn = []
    imgo = []
    src_ = ''
    for src in srcs:
        xn = xn + 1
        bi = src.rfind('/')  # index of backslash
        if bi >= 0:
            n = len(src)
            imgn.append(src[bi + 1:])
            imgo.append(src)
            temp_ = temp_.replace(src, 'cid:' + src[bi + 1:])

    regex = r'<v:imagedata[^>]+src=\"([^\">]+)'
    srcs = re.findall(regex, str(temp_))
    src_ = ''
    for src in srcs:
        xn = xn + 1
        bi = src.rfind('/')  # index of backslash
        if bi >= 0:
            n = len(src)
            imgn.append(src[bi + 1:])
            imgo.append(src)
            temp_ = temp_.replace(src, 'cid:' + src[bi + 1:])

    # fix bad style
    # temp_=temp_.replace("if gte vml 1",'if gte vml 1000')

    textfile = open(prefix + "/email2.html", 'w')
    textfile.write(temp_)
    textfile.close()
    values = {}
    temp = EmailTemplate(template_name=prefix + "/email2.html", values=values)
    ### download attached files
    # templateID_folder = "1Tnw9ShNslKIwt7awqxQQ7Awva7rMXE3T"
    # ONLY UPLOAD IMAGES
    templatefiles = []
    if templateID_folder != "":
        src_ = ''
        fileIds = get_files_in_folder(service, templateID_folder)
        FileNames = []
        for fileId_ in fileIds:
            file_ = service.files().get(fileId=fileId_).execute()
            FileName = file_['title']
            FileName = FileName.lower()
            FileNames.append(FileName)

        ext = ['.gif', '.png', '.jpeg', '.jpg', '.jpeg']
        xn = 0
        fids = []
        fnd = 0
        for FileName in FileNames:
            FileName = FileName.lower()
            xn = xn + 1
            if any(x in FileName for x in ext):
                if any(x in FileName for x in imgn):
                    fnd = 1
                    fids.append(fileIds[xn - 1])
        if fnd > 0:
            templatefiles = download(service, fids, prefix + "/attachments")

    server = MailServer(server_name=servern, username=femail,
                        password=femailp,
                        port=port_, require_starttls=True)
    # lets fix template file by replacing the
    # import lxml.html as LH
    # root = LH.fromstring(str(temp))
    # for el in root.iter('img'):
    #    for ii in range(xn):
    #   if el.attrib['src']==imgo[ii]:
    #       el.attrib['src'] = img[ii]
    #
    # temp=root
    fsubject = subject + ' - ' + fadr_

    msg = MailMessage(from_email=femail, to_emails=[Email_To], reply_to=[Reply_to], subject=fsubject, template=temp,
                      templatefiles=templatefiles, attachments=attachFileNames, qattachment=qname, cc_emails=[Email_CC])

    send(mail_msg=msg, mail_server=server)

    ###delete downloaded files
    # os.remove(templateFileName)
    # for name in attachFileNames:
    #    if (os.path.exists(name)):
    #        os.remove(name)
    # shutil.rmtree(prefix)
    if len(attachFileNames) > 0:
        folder = attachFileNames[0].split("/")
        foldername = folder[len(folder) - 2]
        # shutil.rmtree(path + "/uploads/" + foldername)
    content = {"Email_CC": Email_CC, "Reply_to": Reply_to, "Email_To": Email_To, "templateID_folder": templateID_folder,
               "templateID": templateID, "address": address, "price": price, "name": name, "subject": subject,
               "finddeadline": finddeadline, "attachFileNames": attachFileNames,
               "sent_time": datetime.datetime.now().replace(microsecond=0).strftime('%m/%d/%Y-%H:%M:%S')}
    textfile = open(path + "/log.txt", 'a')
    textfile.write(json.dumps(content) + '<br><br>')
    textfile.close()
    print ("sent email already")
    return json.dumps({"success": "sent email to MAIN " + Email_To})


"""Cron Job"""


def cronJob():
    print ("here")
    lines = open(path + "/queue.txt", 'r').readlines()
    data = {}
    flag = 0
    remaining = ""
    for line in lines:
        if flag == 0:
            data = json.loads(line)
            flag = 1
            print(data)
        else:
            remaining += line
    f = open(path + "/queue.txt", "w")
    f.write(remaining)
    f.close()
    if data != {}:
        EmailSendingUint(Reply_to=data['Reply_to'], Email_To=data['Email_To'],
                         templateID_folder=data['templateID_folder'], templateID=data['templateID'],
                         address=data['address'], price=data['price']
                         , name=data['name'], subject=data['subject'], finddeadline=data['finddeadline'],
                         attachFileNames=data['attachFileNames'], prclim=data['prclim'], quote=data['quote'],
                         Email_CC=data['Email_CC'])


@app.route('/email_queue')
def email_queue():
    lines = open(path + "/queue.txt").readlines()
    data = ""
    for line in lines:
        data += line + "<br><br>"
    return data


@app.route('/email_log')
def email_log():
    data = open(path + "/log.txt", "r").read()
    return data


# add your job here
sched.add_interval_job(cronJob, seconds=10)
if __name__ == '__main__':
    app.run()


