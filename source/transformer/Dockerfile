# Base this image off the Debian ("stretch") release, using Python 3.7
FROM python:3.7-stretch

LABEL Authors="Daniel Sissman <dsissman@getty.edu>, Viktor Grabarchuk <vgrabarchuk@getty.edu>"

# Set our working directory
WORKDIR /

# Later in preparation for deploying our container we need to integrate and test with envconsul...
# COPY --from=getty/envconsul:latest /bin/envconsul /usr/local/bin/envconsul
# COPY --from=getty/envconsul:latest /usr/local/bin/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Copy and install our dependencies from requirements.txt
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

COPY ./source/transformer/app /app
COPY ./source/transformer/tests /tests
COPY ./source/app/di /app/di
COPY ./source/app/database /app/database
COPY ./source/app/graph /app/graph
COPY ./source/app/model /app/model
COPY ./source/app/utilities /app/utilities

COPY ./source/transformer/startup.py /startup.py
COPY ./source/transformer/startup.sh /startup.sh
RUN chmod +x /startup.sh

# Set the default shell to BASH rather than the more basic (DA)SH
SHELL ["/bin/bash", "--login", "-c"]

# Tell Docker to open port 5200; this is the same port as we have configured for use by Flask
EXPOSE 5200

# Later in preparation for deploying our container we need to integrate and test with envconsul...
# ENTRYPOINT [ "docker-entrypoint.sh" ]
# CMD [ "/usr/local/bin/envconsul", "-config=/tmp/config.hcl", "uwsgi", "--http 0.0.0.0:5000", "--manage-script-name", "--mount /=museum-linked-art.app:app" ]
# CMD [ "/bin/bash" ];

# Run our application startup script...
# CMD [ "/startup.sh" ];
