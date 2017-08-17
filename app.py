import pygit2
import json
import boto3
import zipfile
import os
import datetime
import shutil
from pygit2.remote import RemoteCallbacks
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.compat import urlsplit


s3 = boto3.client('s3')
codecommit = boto3.client('codecommit', region_name='ap-northeast-1')
session = boto3.Session()

def getObject(bucket, objectKey):
    try:
        object = s3.get_object(Bucket=bucket, Key=objectKey)
        if 'Body' in object:
            return object['Body'].read()
        else:
            print 'No content in the get object response.'
            return False
    except ClientError as exception:
        print exception.response
        if exception.response['Error']['Code'] == '404':
            return False
        else:
            return None

def sign_request(region, url_to_sign):
    credentials = session.get_credentials()
    signer = SigV4Auth(credentials, 'codecommit', region)
    request = AWSRequest()
    request.url = url_to_sign
    request.method = 'GIT'
    now = datetime.datetime.utcnow()
    request.context['timestamp'] = now.strftime('%Y%m%dT%H%M%S')
    split = urlsplit(request.url)
    # we don't want to include the port number in the signature
    hostname = split.netloc.split(':')[0]
    canonical_request = '{0}\n{1}\n\nhost:{2}\n\nhost\n'.format(
        request.method,
        split.path,
        hostname)
    print 'CanonicalRequest:\n%s', canonical_request
    string_to_sign = signer.string_to_sign(request, canonical_request)
    print 'StringToSign:\n%s', string_to_sign
    signature = signer.signature(string_to_sign, request)
    print 'Signature:\n%s', signature

    return '{0}Z{1}'.format(request.context['timestamp'], signature)

            
def get_cred(theUrl):
    credentials = session.get_credentials()
    credentials = credentials.get_frozen_credentials()

    username = credentials.access_key + '%' + credentials.token
    # secret_access_key = credentials.secret_key

    region = 'ap-northeast-1'
    password = sign_request(region, theUrl)

    cred = pygit2.UserPass(username, password)

    print credentials

    return RemoteCallbacks(credentials=cred)

def clone(repo_url, repo_path):
    print repo_url
    print repo_path

    repo = pygit2.clone_repository(repo_url, repo_path, callbacks=get_cred(repo_url)) # Clones a non-bare repository

def Achive_Folder_To_ZIP(sFilePath, dest = ""):
    """
    input : Folder path and name
    output: using zipfile to ZIP folder
    """
    if (dest == ""):
        zf = zipfile.ZipFile(sFilePath + '.ZIP', mode='w')
    else:
        zf = zipfile.ZipFile(dest, mode='w')
 
    os.chdir(sFilePath)
    #print sFilePath
    for root, folders, files in os.walk("."):
        for sfile in files:
            aFile = os.path.join(root, sfile)
            #print aFile
            zf.write(aFile)
    zf.close()

def initialize():
    for root, dirs, files in os.walk('/tmp'):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

def lambda_handler(event, context):
    # Log the updated references from the event
    references = { reference['ref'] for reference in event['Records'][0]['codecommit']['references'] }
    print("References: "  + str(references))
    
    # Get the repository from the event and show its git clone URL
    repository = event['Records'][0]['eventSourceARN'].split(':')[5]
    try:
        initialize()
    
        response = codecommit.get_repository(repositoryName=repository)
        cloneUrlHttp = response['repositoryMetadata']['cloneUrlHttp']
        repo_path = '/tmp/plumber'
        dest = '/tmp/plumber.zip'

        clone(cloneUrlHttp, repo_path)
        Achive_Folder_To_ZIP(repo_path, dest)
        
        if (os.path.isfile(dest)):
            s3.upload_file(dest, 'plumber-public', 'plumber.zip')
        
    except Exception as e:
        print(e)
        print('Error getting repository {}. Make sure it exists and that your repository is in the same region as this function.'.format(repository))
        raise e
