FROM python:3.10-slim

# RUN apt-get -y install gnupg
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138
RUN apt-get update
RUN apt-get install --yes --no-install-recommends apt-transport-https ca-certificates curl gnupg vim
RUN apt-get clean
RUN apt install libaio1 -y
RUN apt-get install zip -y

RUN apt-get update && apt-get install -y lsb-release && apt-get clean all
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17

# WORKDIR /code

# COPY ./requirements.txt ./
# COPY ./src ./src

# # Install Python Packages
# RUN pip install --no-cache-dir -r requirements.txt

ENV VAULT_ROLE_ID="0b7fbe78-feed-f4b0-4740-effe7c1a27b3"
ENV VAULT_SECRET_ID="7a9ea774-3c9b-7e0b-4253-5852aec2c70f"
ENV GMIServer="Development"
# ENV GRB_LICENSE_FILE=${APP_ROOT/src/gurobi.lic}

# # Setup user for build execution and application runtime
# ENV APP_ROOT=/code
# COPY bin/ ${APP_ROOT}/bin/
# ENV TNS_ADMIN=${APP_ROOT}/bin