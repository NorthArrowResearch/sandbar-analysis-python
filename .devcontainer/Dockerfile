############################################################################################
# Dev Container for riverscapes-tools
############################################################################################
FROM mcr.microsoft.com/devcontainers/python:3.11 AS worker

# Some preliminary dependencies
RUN apt update && apt upgrade -y && apt autoremove -y

RUN apt-get install -y curl wget git build-essential libssl-dev gcc g++ make zsh vim \
                software-properties-common awscli locales

# Python stuff
RUN apt-get install -y python3-pip proj-data proj-bin \
              gdal-bin libgdal-dev libspatialindex-dev \
              python3-matplotlib


# Now follow up on python install
RUN pip install --upgrade pip
RUN pip install numpy==1.23.4 Cython==0.29.23

# https://bobbyhadz.com/blog/python-error-in-package-setup-command-use-2to3-is-invalid
RUN pip install "setuptools<58.0"
# Now install the right version of gdal from the apt-get above
RUN pip install GDAL==$(gdal-config --version)

# Now install any lingering dependencies
COPY requirements.docker.txt /workspaces/requirements.txt
RUN pip --timeout=120 install -r /workspaces/requirements.txt

# Now install  18 
USER vscode
RUN wget https://raw.githubusercontent.com/Riverscapes/environment/master/nar-ys.zsh-theme -O ~/.oh-my-zsh/custom/themes/nar-ys.zsh-theme
RUN wget https://raw.githubusercontent.com/Riverscapes/environment/master/.aliases -O ~/.aliases
RUN wget https://raw.githubusercontent.com/Riverscapes/environment/master/.zshrc -O ~/.zshrc


WORKDIR /workspaces/sandbar-analysis-python
