FROM apache/airflow:2.3.0

ENV AIRFLOW_HOME=/opt/airflow
# Extra packages
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         vim cron wget unixodbc unixodbc-dev\
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

WORKDIR $AIRFLOW_HOME

# Config files
COPY config/airflow.cfg ./airflow.cfg
COPY requirements.txt ./requirements.txt

# requirements
RUN pip install --user -r ./requirements.txt

COPY dags/ dags/
COPY data/ data/
COPY logs/ logs/

