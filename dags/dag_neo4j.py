import logging
from datetime import datetime

import xmltodict
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.neo4j.hooks.neo4j import Neo4jHook

from neo4j_servicer import App

DAG_ID = "dag_neo4j"


def parse_entry(entry):
    response = {
        'name': '',
        'created_at': '',
        'modified': '',
        'version': '',
        'dataset': '',
        'protein': {},
        'genes': {},
        'organism': {},
        'references': [],
        'features': []
    }

    for key_entry, value in entry.items():
        if type(value) == dict:
            if key_entry == 'protein':
                response['protein'] = value
            elif key_entry == 'gene':
                response['genes'] = value
            elif key_entry == 'organism':
                response['organism'] = value
        elif type(value) == list:
            if key_entry == 'reference':
                response['references'] = value
            elif key_entry == 'feature':
                response['features'] = value
        else:
            if key_entry == 'name':
                response['name'] = value
            elif key_entry == '@created':
                response['created_at'] = value
            elif key_entry == '@modified':
                response['modified'] = value
            elif key_entry == '@version':
                response['version'] = value
            elif key_entry == '@dataset':
                response['dataset'] = value
            else:
                print(key_entry)
                print(type(value), value)

    return response


def parse_xml(**kwargs):
    with open('/opt/airflow/data/Q9Y261.xml', 'r') as f:
        data = xmltodict.parse(f.read())
        entry = data['uniprot']['entry']
        response = parse_entry(entry)
        logging.info(response)
        kwargs['ti'].xcom_push(key="entry", value=response)


def create_protein(**kwargs):
    entry = kwargs['ti'].xcom_pull(key="entry", task_ids="parse_xml")
    print(entry)
    neo4j = Neo4jHook(conn_id="neo4j_conn_id")
    app = App(neo4j)
    app.create_protein(entry['protein'], entry['name'])
    app.close()


def create_gene(**kwargs):
    entry = kwargs['ti'].xcom_pull(key="entry", task_ids="parse_xml")
    neo4j = Neo4jHook(conn_id="neo4j_conn_id")
    app = App(neo4j)
    app.create_genes(entry['genes'], entry['name'])
    app.close()


def create_organism(**kwargs):
    entry = kwargs['ti'].xcom_pull(key="entry", task_ids="parse_xml")
    neo4j = Neo4jHook(conn_id="neo4j_conn_id")
    app = App(neo4j)
    app.create_organism(entry['organism'], entry['name'])
    app.close()


def create_reference(**kwargs):
    entry = kwargs['ti'].xcom_pull(key="entry", task_ids="parse_xml")
    neo4j = Neo4jHook(conn_id="neo4j_conn_id")
    app = App(neo4j)
    app.create_references(entry['references'], entry['name'])
    app.close()


def create_feature(**kwargs):
    entry = kwargs['ti'].xcom_pull(key="entry", task_ids="parse_xml")
    neo4j = Neo4jHook(conn_id="neo4j_conn_id")
    app = App(neo4j)
    app.create_features(entry['features'], entry['name'])
    app.close()


with DAG(
    DAG_ID,
    start_date=datetime(2023, 1, 1),
    tags=["example"],
    catchup=False,
) as dag:

    start = DummyOperator(task_id="start")

    load_xml = PythonOperator(
        task_id="parse_xml",
        python_callable=parse_xml,
        provide_context=True,
    )
    protein_task = PythonOperator(
        task_id="create_protein",
        python_callable=create_protein,
        provide_context=True,
    )
    gene_task = PythonOperator(
        task_id="create_gene",
        python_callable=create_gene,
        provide_context=True,
    )
    organism_task = PythonOperator(
        task_id="create_organism",
        python_callable=create_organism,
        provide_context=True,
    )
    reference_task = PythonOperator(
        task_id="create_reference",
        python_callable=create_reference,
        provide_context=True,
    )
    feature_task = PythonOperator(
        task_id="create_feature",
        python_callable=create_feature,
        provide_context=True,
    )

    end = DummyOperator(task_id="end")

    start >> load_xml >> protein_task >> gene_task
    protein_task >> organism_task >> end
    protein_task >> reference_task >> end
    protein_task >> feature_task >> end
