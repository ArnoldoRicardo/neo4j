# Weave Bio Technical Assessment Solution
This repository contains my solution to the technical assessment task for Weave Bio. The solution is designed to extract data from an XML file and load it into a Neo4j graph database using Apache Airflow.

## Requirements
To run this solution, you will need:

- Docker
- Docker Compose

## Installation and Setup

1. Clone this repository to your local machine.

2. Navigate to the root directory of the cloned repository.

3. Execute the following command to start the Docker containers for Airflow and Neo4j:

    ```
    docker-compose up -d
    ```
4. Once the containers are up and running, open a web browser and navigate to localhost:8080 to access the Airflow web interface.

5. In the Airflow web interface, go to Admin > Connections > Add a new connection and create a new connection with the following details:

    * Conn Id: neo4j
    * Conn Type: HTTP
    * Host: neo4j
    * Port: 7474
    * Schema: neo4j
    * Login: neo4j
    * Password: <leave blank>

6. Save the new connection.

7. In the Airflow web interface, go to the DAGs page and enable the xml_to_neo4j DAG.

8. Trigger the DAG by clicking on the Trigger DAG button.

9. Monitor the progress of the DAG in the Airflow web interface.

10. Once the DAG has finished running, verify that the data has been loaded into Neo4j by opening Neo4j Browser at localhost:7474 and executing Cypher queries to inspect the data.
# neo4j
