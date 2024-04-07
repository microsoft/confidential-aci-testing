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

# Install Python Package in Container
RUN apt-get update && apt-get install -y python3-pip
COPY README.md /README.md
COPY c_aci_testing /c_aci_testing
COPY aci /aci
COPY setup.py /
RUN pip install . && python3 setup.py sdist

COPY test/example /example

ENV TARGET=/target
ENV EXAMPLE_PATH=/example

ENTRYPOINT ["python3", "-m"]
