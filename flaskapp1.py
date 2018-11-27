from __future__ import print_function
from apiclient.discovery import build
from apiclient import errors

from httplib2 import Http
from oauth2client import file, client, tools

from flask import *
import json
import os, email, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from apiclient.http import MediaIoBaseDownload
from werkzeug import secure_filename
from flask_cors import CORS
import io
import time
import shutil
import re
import os
import lxml

# import lxml.html as LH
# from bs4 import BeautifulSoup



path = os.path.dirname(__file__)
# modify this to change the Template Directory

app = Flask(__name__)
CORS(app)

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


class MailMessage(object):
    html = False

    def __init__(self, from_email='', to_emails=[], cc_emails=[], reply_to=[], subject='', body='', template=None,
                 attachments=[]):
        self.from_email = from_email
        self.reply_to = reply_to
        self.to_emails = to_emails
        self.cc_emails = cc_emails
        self.subject = subject
        self.template = template
        self.body = body
        self.file_attachments = attachments

    def attach_file(self, path):
        self.file_attachments.append(path)

    def get_message(self):
        if isinstance(self.to_emails, str):
            self.to_emails = [self.to_emails]

        if isinstance(self.reply_to, str):
            self.reply_to = [self.reply_to]

        if isinstance(self.cc_emails, str):
            self.cc_emails = [self.cc_emails]

        if len(self.to_emails) == 0 or self.from_email == '':
            raise ValueError('Invalid From or To email address(es)')

        # msg = MIMEMultipart('alternative')
        msg = MIMEMultipart('alternative')
        msg['To'] = ', '.join(self.to_emails)
        msg['Reply-to'] = ', '.join(self.reply_to)
        msg['Cc'] = ', '.join(self.cc_emails)
        msg['From'] = self.from_email
        msg['Subject'] = self.subject

        if self.template:
            if self.template.html:
                msg.attach(MIMEText(self.template.render(), 'html'))
            else:
                msg.attach(MIMEText(self.template.render(), 'plain'))
        else:
            msg.attach(MIMEText(self.body, 'plain'))

        for attachment in self.file_attachments:
            # ORIG with open(attachment, "rb") as f:
            # ORIGfilename = os.path.basename(attachment)
            fp = open(attachment, 'rb')
            msgImage = MIMEImage(fp.read())
            fp.close()
            cids = attachment.split("/")
            cid = cids[len(cids) - 1]
            msgImage.add_header('Content-ID', '<' + cid + '>')
            msg.attach(msgImage)

        # ORIG part = MIMEApplication(f.read(), Name=filename)
        # ORIG part['Content-Disposition'] = 'attachment; filename="' + str(filename) + '"'
        # ORIG msg.attach(part)
        return msg


class MailServer(object):
    msg = None

    def __init__(self, server_name='smtp.gmail.com', username='<username>', password='<password>', port=587,
                 require_starttls=True):
        self.server_name = server_name
        self.username = username
        self.password = password
        self.port = port
        self.require_starttls = require_starttls


def send(mail_msg, mail_server=MailServer()):
    server = smtplib.SMTP(mail_server.server_name, mail_server.port)
    if mail_server.require_starttls:
        server.starttls()
    if mail_server.username:
        server.login(mail_server.username, mail_server.password)

    server.sendmail(mail_msg.from_email, (mail_msg.to_emails + mail_msg.cc_emails), mail_msg.get_message().as_string())
    server.close()


def getConnection():
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage(path + '/credentials.json')
    creds = store.get()

    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(path + '/client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)

    service = build('drive', 'v2', http=creds.authorize(Http()))
    return service


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


@app.route('/')
def hello_world():
    return render_template('index.html')


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
        elif 'attachFiles' not in request.files:
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


## Get file list of google drive
@app.route('/fileList')
def fileList():
    # Setup the Drive v2 API
    service = getConnection()

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

        templateID_folder = ""
        if 'templateID_folder' in request.form:
            templateID_folder = request.form['templateID_folder']
        elif 'attachFiles' not in request.files:
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
        ## Define values which are needed to exchange with email text.
        values = {}
        # values['username'] = 'mail@gmail.com'
        # values['from'] = 'mail@gmail.com'
        # values['url'] = ''

        ## Sending email to reply_to
        femail = 'theresa@la-retrofit.com'
        femailp = 'Test123456@'

        if '@la-retrofit.com' in femail:
            servern = 'smtp.office365.com'
            port_ = 587
        if '@gmail.com' in femail:
            servern = 'smtp.gmail.com'
            port_ = 587

        temp = EmailTemplate(template_name=templateFileName, values=values)
        temp_ = str(temp.render())
        # WE FIX IMAGES

        # rep_ = r'windows-1252'
        # temp_ = unicode(temp_, "u")
        temp_ = re.sub(r'[^\x00-\x7F]+', ' ', temp_)
        # temp_=temp_.decode('utf-8')

        # REPLACES THE CONTENT OF EMAIL
        # REPLACES THE CONTENT OF EMAIL
        # REPLACES THE CONTENT OF EMAIL

        #	temp_=temp_.replace("Hi ,","Hi "+name+",")
        #        temp2="BUILDING 1 Address:<br>"+fulladdress
        #	temp_=temp_.replace("BUILDING 1 Address:",temp2)

        #        if (prclim == ''):
        #          temp_=temp_.replace("%PRICE%",'$'+price);
        #        else:
        #          temp_=temp_.replace("%PRICE%",'$'+price+ '  ('+prclim_+')');



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
                tempstr = src[bi + 1:]
                tempstr2 = src[:bi + 1]
                temp_ = temp_.replace(src, 'cid:' + tempstr)
                temp_ = temp_.replace(tempstr2, 'cid:')
                temp_ = temp_.replace('if gte vml 1', 'if gte vml 100')

        textfile = open(prefix + "/email2.html", 'w')
        textfile.write(temp_)
        textfile.close()
        values = {}
        temp = EmailTemplate(template_name=prefix + "/email2.html", values=values)
        ### download attached files
        # templateID_folder = "1Tnw9ShNslKIwt7awqxQQ7Awva7rMXE3T"
        # ONLY UPLOAD IMAGES
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
            tmp = ''
            for FileName in FileNames:
                FileName = FileName.lower()
                xn = xn + 1
                if any(x in FileName for x in ext):
                    if any(x in FileName for x in imgn):
                        fnd = 1
                        fids.append(fileIds[xn - 1])
                        tmp = tmp + FileName + ' '
            if fnd > 0:
                attachFileNames = download(service, fids, prefix + "/attachments")
                # return tmp

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
        msg = MailMessage(from_email=femail, to_emails=[Email_To], reply_to=[Reply_to], subject=subject, template=temp,
                          attachments=attachFileNames)

        send(mail_msg=msg, mail_server=server)

        ## delete downloaded files
        # os.remove(templateFileName)
        # for name in attachFileNames:
        #    if (os.path.exists(name)):
        #        os.remove(name)
        # shutil.rmtree(prefix)
        return json.dumps({"success": "sent email to MAIN " + Email_To})


if __name__ == '__main__':
    app.run()
