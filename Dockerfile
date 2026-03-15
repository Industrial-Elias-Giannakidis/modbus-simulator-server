FROM python:3.13-slim

WORKDIR /app

COPY helpers/ ./helpers/
COPY static/ ./static/
COPY docs/ ./docs/
COPY index.py modbus_server.py \
     register_configs.json default_register_config.json \
     server_config.json ./

RUN pip install --no-cache-dir aiohttp pymodbus

ARG MODBUS_PORT=5020
ARG API_PORT=8080

ENV MODBUS_PORT=${MODBUS_PORT}
ENV API_PORT=${API_PORT}

EXPOSE ${MODBUS_PORT}
EXPOSE ${API_PORT}

CMD ["python", "index.py"]
