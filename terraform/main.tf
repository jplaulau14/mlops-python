terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-west-2"
}

resource "aws_security_group" "ctgan_sg" {
  name        = "CTGANSynthesizerSG"
  description = "Allow SSH and port 5000 for Flask app"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_ami" "amazon-2" {
  most_recent = true
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-ebs"]
  }
  owners = ["amazon"]
}

resource "aws_instance" "ctgan_instance" {
  ami           = data.aws_ami.amazon-2.id 
  instance_type = "t2.medium"
  key_name      = aws_key_pair.ctgan_keypair.key_name

  vpc_security_group_ids = [aws_security_group.ctgan_sg.id]
  iam_instance_profile   = "EC2S3FullAccess"
  tags = {
    Name = "CTGANSynthesizer"
  }

  ebs_block_device {
    device_name = "/dev/xvda"
    volume_type = "gp2"
    volume_size = 30
  }


#   user_data = <<-EOF
#               #!/bin/bash
#               docker pull <repositoryUri>:latest
#               docker run -p 5000:5000 <repositoryUri>:latest
#               EOF
}

resource "aws_key_pair" "ctgan_keypair" {
  key_name   = "data_synthesizer_key"
  public_key = file("~/Desktop/mlops-python/terraform/data_synthesizer_key.pub")
}

# Output the public IP address of the instance
output "public_ip" {
  value = aws_instance.ctgan_instance.public_ip
}