# The base-adapter image is built automatically by the integration SDK.
FROM base-adapter:python-1.2.0
COPY commands.cfg .
COPY adapter_requirements.txt .
RUN pip3 install -r adapter_requirements.txt --upgrade
COPY app app
