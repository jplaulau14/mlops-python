Deploying Lambda function using ECR
----------------
1. Build the docker image
```
docker build --platform linux/amd64 -t model-inference .
```
2. If not already logged in, login to ECR
```
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.us-west-2.amazonaws.com
```

3. If repository does not exist, create it:
```
aws ecr create-repository --repository-name model-inference --region us-west-2 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
```

4. Get the repository URI:
```
aws ecr describe-repositories --repository-names model-inference --region us-west-2
```

5. Tag the image:
```
docker tag model-inference:latest <repository_uri>:latest
```

6. Push the image to ECR:
```
docker push <repository_uri>:latest
```
