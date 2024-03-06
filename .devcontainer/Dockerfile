# Use the official image as a parent image
FROM osgeo/gdal:ubuntu-full-3.6.2

# Set the working directory in the container
WORKDIR /usr/src/app

# Install necessary tools for VSCode DevContainers
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends curl ca-certificates 2>&1 \
    && curl -sSL https://aka.ms/InstallAzureCLIDeb | bash \
    && apt-get -y install git iproute2 procps lsb-release \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y python3-pip zsh wget git

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create a non-root user to use if preferred - see https://aka.ms/vscode-remote/containers/non-root-user.
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo wget \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    #
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

USER $USERNAME

# Upgrade pip to latest
RUN python3 -m pip install --upgrade pip

# Install oh-my-zsh
RUN sh -c "$(wget https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O -)" \
    && wget https://raw.githubusercontent.com/Riverscapes/environment/master/nar-ys.zsh-theme -O ~/.oh-my-zsh/custom/themes/nar-ys.zsh-theme \
    && wget https://raw.githubusercontent.com/Riverscapes/environment/master/.aliases -O ~/.aliases \
    && wget https://raw.githubusercontent.com/Riverscapes/environment/master/.zshrc -O ~/.zshrc

# Install python requirements
COPY requirements.docker.txt .
RUN pip3 install -r requirements.docker.txt

# Set the PYTHONPATH environment variable
ENV PYTHONPATH "/usr/src/app"

# Set the default shell to zsh rather than sh
ENV SHELL /bin/zsh