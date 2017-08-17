aws-lambda-python-codecommit-s3-deliver
===

This lambda function can automatic pack the CodeCommit repository to S3 bucket.

### Quick start

1. Download the aws-lambda-python-codecommit-s3-deliver .zip file
2. Go to the [Lambda console](https://ap-northeast-1.console.aws.amazon.com/lambda/home?region=ap-northeast-1#/create/configure-function) and create a Lambda function
3. Add trigger: CodeCommit, events: Push to existing branch, branch name: master
3. Upload the .zip file
4. Please select **Create a new IAM Role from template**
5. Go to the [IAM Role Console](https://console.aws.amazon.com/iam/home?#/roles)
6. Please select the Lambda IAM Role
7. Add the inline policy below

IAM Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1501197956000",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR_BUCKET",
                "arn:aws:s3:::YOUR_BUCKET/*"
            ]
        },
        {
            "Sid": "Stmt1502993499000",
            "Effect": "Allow",
            "Action": [
                "codecommit:GetBlob",
                "codecommit:GetBranch",
                "codecommit:GetCommit",
                "codecommit:GetRepository",
                "codecommit:GetRepositoryTriggers",
                "codecommit:GitPull",
                "codecommit:ListBranches",
                "codecommit:TestRepositoryTriggers"
            ],
            "Resource": [
                "arn:aws:codecommit:ap-northeast-1:YOUR_ACCOUNT_ID:YOUR_CODECOMMIT_REPOSITORY"
            ]
        }
    ]
}
```

9. Set up the parameters regarding your S3 bucket and CodeCommit repository


### Test

This function would be triggerred when the CodeCommit is having the Push event. You can check the .zip file in your S3 bucket after any new push event.

```
git push -u origin master
```
