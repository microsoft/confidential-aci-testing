FROM ubuntu:latest

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install Docker in Docker
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    lsb-release
RUN curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Azure CLI
RUN apt-get update && apt-get install -y python3-distutils
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install Python Deps
RUN apt-get update && apt-get install -y python3-pip
COPY requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

COPY tools /

ENV TARGET=/target