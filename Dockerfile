FROM jupyter/scipy-notebook:7aa954ab78d1

USER root
RUN apt-get update && apt-get install wget -y

# Make sure the contents of our repo are in ${HOME}
COPY . ${HOME}
WORKDIR ${HOME}

USER ${NB_USER}
RUN pip install --no-cache-dir notebook
RUN python -m fable_py install --user

# Install.Net
RUN wget https://dot.net/v1/dotnet-install.sh
RUN chmod 777 ./dotnet-install.sh
RUN ./dotnet-install.sh -c 5.0
ENV PATH="$PATH:${HOME}/.dotnet"

RUN dotnet tool restore
