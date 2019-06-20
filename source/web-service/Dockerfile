# Base this image off the Debian ("stretch") release, using Python 3.7
FROM python:3.7-stretch

MAINTAINER Daniel Sissman <dsissman@getty.edu>
MAINTAINER Viktor Grabarchuk <vgrabarchuk@getty.edu>

# Set our working directory to /app
WORKDIR /app

# Later in preparation for deploying our container we need to integrate and test with envconsul...
# COPY --from=getty/envconsul:latest /bin/envconsul /usr/local/bin/envconsul
# COPY --from=getty/envconsul:latest /usr/local/bin/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Copy and install our dependencies from requirements.txt
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY ./source/app /app

COPY ./source/web-service/app/startup.py /app/startup.py
# RUN chmod +x /app/startup.py

COPY ./source/web-service/app/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Tell Docker to open port 5100; this is the same port as we have configured for use by Flask
EXPOSE 5100

# Later in preparation for deploying our container we need to integrate and test with envconsul...
# ENTRYPOINT [ "docker-entrypoint.sh" ]
# CMD [ "/usr/local/bin/envconsul", "-config=/tmp/config.hcl", "uwsgi", "--http 0.0.0.0:5000", "--manage-script-name", "--mount /=museum-linked-art.app:app" ]

# For now, run our application startup script directly...
CMD [ "/app/startup.sh" ];