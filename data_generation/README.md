Local testing:
----------------
1. Build the docker image
```
docker build -t data_generation .
```
2. Run the docker image
```
docker run -p 5001:5000 -v ~/.aws:/root/.aws data_generation
```
3. Test the API to generate data 
```
curl http://localhost:5001/generate_data
```
4. Test the API endpoint that evaluates the generated data
```
curl http://localhost:5001/evaluate_quality
```

Deploying to an AWS EC2 instance:
-----------------
This assumes that you already have an EC2 instance running and you can successfully SSH into it locally.
1. Zip the contents that you need for deployment
```
zip -r app.zip app.py requirements.txt Dockerfile train_synthesizer.py gx
```
2. Copy the zip file to the EC2 instance
```
scp -i <path_to_pem_file> app.zip <ec2_user>@<ec2_public_dns>:~/app.zip
```
3. SSH into the EC2 instance
```
ssh -i <path_to_pem_file> <ec2_user>@<ec2_public_dns>
```
4. Update the EC2 instance and install docker
```
sudo yum update -y
sudo yum install docker -y
```
5. Unzip the contents
```
unzip app.zip
```
6. Run docker then build the image
```
sudo service docker start
docker build -t data_generation .
```
7. Run the docker image
```
docker run --name data_generation --log-driver=awslogs --log-opt awslogs-group=data-synthesizer-logs --log-opt awslogs-region=us-west-2 -p 5000:5000 data_generation:latest
```
8. Test the API to generate data 
```
curl http://<ec2_public_dns>:5000/generate_data
```
9. Test the API endpoint that evaluates the generated data
```
curl http://<ec2_public_dns>:5000/evaluate_quality
```