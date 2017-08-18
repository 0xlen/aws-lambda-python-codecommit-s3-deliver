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

REGION = os.getenv('AWS_REGION')
S3_BUCKET = os.getenv('S3_BUCKET', '')
FILE_NAME = os.getenv('FILE_NAME', 'repo.zip')
BRANCH = os.getenv('BRANCH', 'master')

s3 = boto3.client('s3')
codecommit = boto3.client('codecommit', region_name=REGION)
session = boto3.Session()


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
    print 'CanonicalRequest:\n%s' % canonical_request
    string_to_sign = signer.string_to_sign(request, canonical_request)
    print 'StringToSign:\n%s' % string_to_sign
    signature = signer.signature(string_to_sign, request)
    print 'Signature:\n%s' % signature

    return '{0}Z{1}'.format(request.context['timestamp'], signature)

            
def get_cred(repo_url, repo_region):
    credentials = session.get_credentials()
    credentials = credentials.get_frozen_credentials()

    username = credentials.access_key + '%' + credentials.token

    password = sign_request(repo_region, repo_url)

    cred = pygit2.UserPass(username, password)

    print credentials

    return RemoteCallbacks(credentials=cred)

def clone(repo_url, repo_region, repo_path):
    print repo_url
    print repo_region
    print repo_path

    repo = pygit2.clone_repository(repo_url, repo_path, checkout_branch=BRANCH, callbacks=get_cred(repo_url, repo_region))

def zipRepository(repo_path, dest = ""):
    if (dest == ""):
        zf = zipfile.ZipFile(repo_path + '.zip', mode='w')
    else:
        zf = zipfile.ZipFile(dest, mode='w')
 
    os.chdir(repo_path)
    for root, folders, files in os.walk("."):
        for file in files:
            file_path = os.path.join(root, file)
            zf.write(file_path)
    zf.close()

def initialize():
    for root, dirs, files in os.walk('/tmp'):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

def lambda_handler(event, context):

    if S3_BUCKET == '' or S3_BUCKET == None:
        return 'Please specify the S3_BUCKET value in the environment variable.'

    # Log the updated references from the event
    references = { reference['ref'] for reference in event['Records'][0]['codecommit']['references'] }
    print("References: "  + str(references))
    
    # Get the repository from the event and show its git clone URL
    repository = event['Records'][0]['eventSourceARN'].split(':')[5]
    try:
        # Clear the /tmp if the lambda is having concurrency requests
        initialize()
    
        response = codecommit.get_repository(repositoryName=repository)
        cloneUrlHttp = response['repositoryMetadata']['cloneUrlHttp']

        # Generate repository path by time
        repo_path = os.path.join('/tmp', datetime.datetime.now().strftime('%H%M%S%f'))
        dest = os.path.join('/tmp', FILE_NAME)

        clone(cloneUrlHttp, REGION, repo_path)
        zipRepository(repo_path, dest)
        
        if (os.path.isfile(dest)):
            s3.upload_file(dest, S3_BUCKET, FILE_NAME)
        else:
            return 'No compressed file exists'
        
    except Exception as e:
        print(e)
        print('Error getting repository {}. Make sure it exists and that your repository is in the same region as this function.'.format(repository))
        raise e
