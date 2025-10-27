FROM python:3.10-slim

# adding ffmpeg and slim

RUN apt-get -y update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*
# RUN apt-get -y update 


# set display port to avoid crash
ENV DISPLAY=:99

# upgrade pip
RUN pip install pip==23.0.1


RUN python -m pip install pip==23.0.1

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt

COPY . .

CMD ["/bin/bash", "+x", "/entrypoint.sh"]
